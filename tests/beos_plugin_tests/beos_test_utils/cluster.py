
import os
import json
import time
import socket
import requests
import datetime
import threading
import collections

from beos_test_utils.beosnode			import BEOSNode
from beos_test_utils.logger			 import log
from beos_test_utils.summarizer		import Summarizer

from cd_scripts import eosio_rpc_actions
from cd_scripts import eosio_rpc_client
from cd_scripts import eosio_tools
from cd_scripts import deploy
from cd_scripts import config

class Cluster(object):
	user_name = list("aaaaaaaaaaaa")
	producer_block_cycle = 12

	def __init__(self, _bios_node, _producers_nr, _producers_per_node, _file):
		self.producers_nr = _producers_nr
		self.file = _file
		self.bios = _bios_node
		self.bios_address = "{0}:{1}".format(self.bios.node_data.node_ip, int(self.bios.node_data.node_port)+9876)
		self.nodes = []
		self.number_of_producers = _producers_nr
		self.producers_per_node = _producers_per_node + 1
		self.producers = collections.OrderedDict()
		self.bios_th = None
		self.mock_producers = collections.OrderedDict()

	def wait_full_jurisdiction_cycle(self):
		bufor = 10
		waiting_blocks = (Cluster.producer_block_cycle * self.number_of_producers * self.producers_per_node) + bufor
		log.info("Wait {0} blocks for end of turn for each producer. We wait that long for jurisdiction change to take effect.".format(waiting_blocks))
		self.bios.wait_n_blocks(waiting_blocks)
		log.info("Proceed.")

	def generate_user_name(self):
		name = list(Cluster.user_name)
		Cluster.user_name[0] = chr(ord(Cluster.user_name[0]) + 1)
		for i, _ in enumerate(Cluster.user_name):
			if ord(Cluster.user_name[i]) > ord('z'):
				Cluster.user_name[i] = 'a'
				Cluster.user_name[i+1] = chr(ord(Cluster.user_name[i+1]) + 1)
		return ''.join(name)

	def create_mock_producer(self, summary : Summarizer = None):
		if len(self.mock_producers) == 0:
			return None
		user = list(self.mock_producers.items())[0]
		resINT_1, _ = self.bios.make_cleos_call([ "wallet", "import", "-n", "beos_master_wallet", "--private-key", user[1]["prv_active"]])
		resINT_2, _ = self.bios.make_cleos_call([ "wallet", "import", "-n", "beos_master_wallet", "--private-key", user[1]["prv_owner"]])
		resINT_3, _ = self.bios.make_cleos_call(["create", "account", "beos.gateway", user[0], user[1]["pub_active"], user[1]["pub_owner"], "--transfer-ram"])
		if summary:
			summary.equal(0, resINT_1)
			summary.equal(0, resINT_2)
		if resINT_1 + resINT_2 + resINT_3 != 0:
			return None
		else:
			return user[0]

	def reg_mock_producer(self, producer_name : str, summary : Summarizer = None):
		if producer_name not in self.mock_producers.keys():
			return False		
		data = self.mock_producers[producer_name]
		resINT, _ = self.bios.make_cleos_call([ "system", "regproducer", producer_name, data["pub_active"], data["url"], "0"])
		if summary:
			summary.equal(0, resINT)
		if resINT:
			return False
		else:
			self.producers[producer_name] = self.mock_producers.pop(producer_name)
			self.producers = collections.OrderedDict(sorted(self.producers.items()))
			return True

	def init_create_nodes(self):
		data = os.path.split(self.file)
		cdir = data[0] if data[0] else "."
		cfile = data[1]
		ip = self.bios.node_data.node_ip
		start_port = self.bios.node_data.node_port
		ports = self.get_free_ports(ip, int(start_port), self.number_of_producers)
		for port in ports:
			node = BEOSNode(ip, port, self.bios.node_data.keosd_ip,
				self.bios.node_data.keosd_port, self.bios.node_data.wallet_name, self.bios.cleos.path_to_cleos)
			node.set_node_dirs(cdir+"/node/"+cfile, cdir+"/logs/"+cfile, None, True)
			self.nodes.append(node)


	def create_key(self):
		_, mess = self.bios.make_cleos_call(["create", "key", "--to-console"])
		mess = mess.split()
		return mess[5], mess[2]


	def prepare_config(self):
		config.NODEOS_PORT = self.bios.node_data.node_port
		config.PRODUCERS_ARRAY = self.producers 
		config.NODEOS_WORKING_DIR = self.bios.working_dir	+ "/{0}-".format(self.bios.node_data.node_port)
		config.PRODUCER_NAME = self.bios.node_data.node_port
		config.START_NODE_INDEX = "node"
		config.BIOS_LOG_FILE_NAME = self.bios.log_file_path


	def prepare_producers_array(self):
		for _ in range(0, self.number_of_producers*self.producers_per_node):
			name = self.generate_user_name()
			pua, pra = self.create_key()
			puo, pro = self.create_key()
			if _ % self.producers_per_node != self.producers_per_node-1:
				self.producers[name] = {"pub_active":pua,"prv_active":pra,"pub_owner":puo,"prv_owner":pro,"url":"https://{0}.proda.htms".format(name)}
			else:
				self.mock_producers[name] = {"pub_active":pua,"prv_active":pra,"pub_owner":puo,"prv_owner":pro,"url":"https://{0}.proda.htms".format(name)}

	def wait_for_bios_start(self):
		for _ in range(60):
			try:
				head_block_num = self.bios.get_url_caller().chain.get_info()["head_block_num"]
				if head_block_num > 0:
					return True
			except:
				time.sleep(1)
		raise Exception("Bios initialization failuer: {wait_for_bios_start}")


	def create_and_run_nodes(self):
		self.wait_for_bios_start()
		self.init_create_nodes()
		nr = 0
		for idx, prod in enumerate(self.producers):
			log.info("Adding producer {0} to node {1}".format(prod, nr))
			self.nodes[nr].user_name = Cluster.user_name
			self.nodes[nr].add_producer_to_config(prod, self.producers[prod]["pub_active"])
			self.producers[prod]["node"] = self.nodes[nr]
			if idx % self.producers_per_node == self.producers_per_node - 1:
				log.info("increasing nr")
				nr += 1
		
		for node in self.nodes:
			node.run_node(self.bios_address, True, self.bios.working_dir + "/{0}-{1}/genesis.json".format(self.bios.node_number, self.bios.node_name))


	def initialize_bios(self):
		self.bios.log_file_path = self.bios.log_path+"/{0}-{1}-{2}-{3}.log".format("nodeos", datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S"), self.bios.node_number, self.bios.node_name)
		self.prepare_producers_array()
		self.prepare_config()
		self.producers = concatenate_dictionaries(self.producers, self.mock_producers)
		th = threading.Thread(target=self.create_and_run_nodes)
		th.start()
		deploy.initialize_beos(config)
		th.join()
		self.producers = dictionaries_diffrence(self.producers, self.mock_producers)
		self.bios.wait_n_blocks(20)


	def stop_all(self, _stop_bios = False):
		for node in self.nodes:
			try:
				node.stop_node()
			except Exception as _ex:
				log.info("Fail to stop node {0}".format(node.node_name))
		deploy.finalize_beos_initialization(config)

	def get_node(self, _nr):
		if _nr > len(self.nodes):
			log.info("Error: index to great")
			return None
		else:
			return self.nodes[_nr]


	def get_free_ports(self, _ip, _start_port, _nr_of_required_ports):
		assert _nr_of_required_ports > 0
		port = _start_port + 1
		ports = []
		while _nr_of_required_ports > 0:
			so = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
			try:
				so.bind((_ip, port))
				so.close()
				ports.append(port)
				_nr_of_required_ports = _nr_of_required_ports - 1
			except socket.error :
				pass
			port = port + 1
		return ports

	#if using this methode make sure, that schedule is stable, and no pending schemes
	def accelerate_nodes(self, _type, _time, ):
		def wait_for_new_producer(_producer = None):
			_, result = self.bios.make_cleos_call(["get", "info"])
			result = json.loads(result)
			head_block_prod = _producer or result["head_block_producer"]
			new_head_block_prod = None
			log.info("Waiting for new producer.")
			while True:
				_, result = self.bios.make_cleos_call(["get", "info"])
				result = json.loads(result)
				new_head_block_prod = result["head_block_producer"]
				if head_block_prod != new_head_block_prod:
					log.info("New producer `{0}`, previous producer `{1}`".format(new_head_block_prod, head_block_prod))
					break
				time.sleep(0.5)
				log.info("Wait...")
			return new_head_block_prod

		def accelerate_mock_time(_node):
			accelerate_url = "http://{0}:{1}/v1/test_producer/accelerate_mock_time".format(node.node_data.node_ip, node.node_data.node_port)
			accelerate_data = {"time":_time, "type":_type}
			result = requests.post(url=accelerate_url, json=accelerate_data)
			log.info("Node `{0}` acceleration mock status `{1}`".format(accelerate_url, result.text))
			
		def accelerate_time(_node):
			accelerate_url = "http://{0}:{1}/v1/test_producer/accelerate_time".format(node.node_data.node_ip, node.node_data.node_port)
			accelerate_data = {"time":_time, "type":_type}
			result = requests.post(url=accelerate_url, json=accelerate_data)
			log.info("Node `{0}` acceleration mock status `{1}`".format(accelerate_url, result.text))

		bios_url = "http://{0}:{1}/v1/test_producer/accelerate_mock_time".format(self.bios.node_data.node_ip, self.bios.node_data.node_port)
		accelerate_data = {"time":_time, "type":_type}
		result = requests.post(url=bios_url, json=accelerate_data)
		log.info("Bios `{0}` acceleration status `{1}`".format(bios_url, result.text))
		current_prod = wait_for_new_producer()
		already_accelerated = []
		for name, item in self.producers.items():
			if current_prod != name:
				node = item["node"]
				if node not in already_accelerated:
					accelerate_mock_time(node)
					already_accelerated.append(node)
		wait_for_new_producer(current_prod)
		node = self.producers[current_prod]["node"]
		accelerate_mock_time(node)
		already_accelerated = []
		for name, item in self.producers.items():
			node = item["node"]
			if node not in already_accelerated:
				accelerate_time(node)
				already_accelerated.append(node)
		log.info("Acceleration complete.")

def concatenate_dictionaries(summand_1 : collections.OrderedDict, summand_2 : collections.OrderedDict, sort : bool = True):
	if summand_1 == None or summand_2 == None:
		try:
			raise AttributeError("Invalid arguments")
		except:
			raise
	to_return = list(summand_1.items())
	to_return.extend(list(summand_2.items()))
	if sort:
		return collections.OrderedDict(sorted(to_return))
	else:
		return collections.OrderedDict(to_return)

def dictionaries_diffrence(minuend : collections.OrderedDict, substrahent : collections.OrderedDict, sort : bool = True):
	if minuend == None or substrahent == None:
		try:
			raise AttributeError("Invalid arguments")
		except:
			raise

	to_return = list()
	for name, data in minuend.items():
		if name not in substrahent:
			to_return.append((name, data))
	
	if sort:
		return collections.OrderedDict(sorted(to_return))
	else:
		return collections.OrderedDict(to_return)
