#!/usr/bin/python3

# Scenario based on test : [5.2]-Basic-issue-test

import os
import sys
import time
import datetime 

if os.path.exists(os.path.dirname(os.path.abspath(__file__))+ "/logs/"+ __file__):
    exit(0)

currentdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(os.path.dirname(currentdir)))
from beos_test_utils.beos_utils_pack import init, ActionResult, ResourceResult, VotersResult

if __name__ == "__main__":
	try:
		node, summary, args, log = init(__file__)
		node.run_node()

		accounts = node.create_accounts(1, "5.0000 BTS")
		tester = accounts[0].name
		
		#Changeparams
		newparams = {
			"beos" : {
				"starting_block" : 10,
				"next_block" : 0, 
				"ending_block" : 30,
				"block_interval" : 5, 
				"trustee_reward" : 1000000
			},
			"ram" : {
				"starting_block" : 10,
				"next_block" : 0, 
				"ending_block" : 20,
				"block_interval" : 5, 
				"trustee_reward" : 0 
			},
			"proxy_assets" : [ "0.0000 BTS"],
			"ram_leftover" : 300000,
			"starting_block_for_initial_witness_election":120
		}

		node.changeparams(newparams)
		#node.changeparams(["0.0000 BTS"], 120, [10,0,30,5,1000000], [10,0,20,5,0], 300000)
		
		#Changes in _ram_bytes values [AD 1] due to this commit: 93430498700a04b8bb49612ebbddffcc144e627c, from 12 Jul, 2019

		#Actions
		summary.user_block_status(node, tester, ResourceResult(_balance="5.0000 BTS",_net_weight="0.0000 BEOS",_cpu_weight="0.0000 BEOS",_ram_bytes=5448))
		node.wait_till_block(10)
		summary.action_status(node.issue(_to=tester,_quantity="5.0000 BTS",_memo="",_from="beos.gateway") )
		node.wait_till_block(12)
		
		#[AD 1] Previous _ram_bytes = 10666672114
		summary.user_block_status(node,tester, ResourceResult(_balance="10.0000 BTS",_net_weight="367121673.1379 BEOS",_cpu_weight="367121673.1380 BEOS",_ram_bytes=10666672052))
		node.wait_till_block(15)
		summary.action_status(node.issue(_to=tester,_quantity="5.0000 BTS",_memo="",_from="beos.gateway") )
		node.wait_till_block(17)

		#[AD 1] Previous _ram_bytes = 21333338781
		summary.user_block_status(node, tester, ResourceResult(_balance="15.0000 BTS",_net_weight="734243346.2758 BEOS",_cpu_weight="734243346.2760 BEOS",_ram_bytes=21333338656))
		node.wait_till_block(20)
		summary.action_status(node.issue(_to=tester,_quantity="5.0000 BTS",_memo="",_from="beos.gateway") )
		node.wait_till_block(22)

		#[AD 1] Previous _ram_bytes = 32000005448
		summary.user_block_status(node, tester, ResourceResult(_balance="20.0000 BTS",_net_weight="1101365019.4137 BEOS",_cpu_weight="1101365019.4140 BEOS",_ram_bytes=32000005261))
	except Exception as _ex:
		log.exception("Exception `{0}` occures while executing `{1}` tests.".format(str(_ex), __file__))
	finally:
		summary_status = summary.summarize()
		node.stop_node()
		exit(summary_status)
