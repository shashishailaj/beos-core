import json
import time
import threading 
import requests
import datetime

from eosrpcexecutor import EOSRPCExecutor

class TestScenarios(object):
    def __init__(self, _nodeos_addres, _nodeos_port, _wallet_address, _wallet_port):
        self.summary_file = "Scenarios_summary_"+str(datetime.datetime.now())[:-7]
        self.actions      = None
        self.scenarios    = None
        self.scenariosNr  = None
        self.blockNumber  = 0
        self.eos_rpc      = EOSRPCExecutor(_nodeos_addres, _nodeos_port, _wallet_address, _wallet_port)
        self.load_scenarios()

        self.blockGetter = threading.Thread(target=self.block_id_getter)
        self.blockGetter.setDaemon(daemonic=True)
        self.runScenarios = threading.Event()
        self.runScenarios.set()
        self.askForBlockNumber = threading.Event()
        self.blockGetter.start()
        

    def __iter__(self):
        return self

   
    def __next__(self):
        if self.scenariosNr == None:
            self.scenariosNr = 0
        else:
            self.scenariosNr += 1
            if self.scenariosNr == len(self.scenarios):
                raise StopIteration
        return self

    def get_current_scenario(self):
        if self.scenarios:
            return self.scenarios[self.scenariosNr]["name"]
        else:
            return "Scenarios was not even inited."

 
    def block_id_getter(self):
        while self.runScenarios.is_set():
            while self.askForBlockNumber.is_set():
                blockNumber = self.eos_rpc.get_info()
                self.blockNumber = int(blockNumber["head_block_num"])
                time.sleep(0.25)
            self.blockNumber = 0


    def load_scenarios(self):
        try:
            with open("scenarios.json") as scenarios:
                self.scenarios = json.load(scenarios)["scenarios"]
        except Exception as _ex:
            print("Error while loading scenarios ", str(_ex))
            exit(1)

 
    def get_scenario_summary(self, _symbol="PXBTS"):
        self.askForBlockNumber.clear()
        expected_result_for_user = self.scenarios[self.scenariosNr]["expected_results"]
        with open(self.summary_file,"a+") as sf:
            sf.writelines("[SCENARIO] :%s\n"%(self.scenarios[self.scenariosNr]["name"]))
            sf.writelines("############# SUMMARY #############\n")
            for expected in expected_result_for_user:
                user = expected["user"]
                balance = self.eos_rpc.get_currency_balance(user, _symbol)
                result = self.eos_rpc.get_account(user)
                total_resources = result["total_resources"] if "total_resources" in result else None
                total_resources["balance"]=balance["balance"]
                at_end = expected["at_end"] if "at_end" in expected else None
                error = False
                if total_resources and at_end:
                    sf.writelines("[INFO] CHECKING VALUES FOR ACCOUNT %s\n"%(user))
                    for key, value in at_end.items():
                        if at_end[key] == total_resources[key]:
                            sf.writelines("[OK] VALUE FOR %s IS AS EXPECTED \n"%(key))
                        else:
                            sf.writelines("[ERROR] VALUE %s FOR %s DOES NOT MATCH EXPECTED ONE %s\n"%( total_resources[key], key, at_end[key]))
                            error = True
                else:
                    if not total_resources and not at_end:
                        sf.writelines("[OK] BOTH `AT_END` AND `TOTAL_RESOURCES` ARE NOT AVAILABLE FOR %s \n"%(user))
                    if total_resources:
                        error = True
                        sf.writelines("[ERROR] `AT_END` IS NOT DEFINED FOR USER %s WHILE `TOTAL_RESOURCES` IS AVAILABLE\n"%(user))
                    if at_end:
                        error = True
                        sf.writelines("[ERROR] `TOTAL_RESOURCES` IS NOT DEFINED FOR USER %s WHILE `AT_END` IS AVAILABLE\n"%(user))
                if not error:
                    sf.writelines("[OK] ALL VALUES FOR %s ARE OK\n"%(user))
            sf.writelines("###################################\n")


    def wait_for_end(self):
        scenario_block = self.scenarios[self.scenariosNr]["scenario_blocks"]
        while scenario_block >= self.blockNumber:
            time.sleep(0.5)


    def set_scenario_params(self):
        params = self.scenarios[self.scenariosNr]["params"]
        self.eos_rpc.prepare_and_push_transaction(params)


    def make_scenario_actions(self):
        self.set_scenario_params()
        return self.execute_scenatio_actions()

    def stop_scenarios(self):
        self.runScenarios.clear()
        self.askForBlockNumber.clear()

    def execute_scenatio_actions(self):
        if not self.askForBlockNumber.is_set():
            self.askForBlockNumber.set()
        self.actions = sorted(self.scenarios[self.scenariosNr]["actions"], key=lambda k: k['start_block'])
        if self.actions:
            for action in self.actions:
                startBlock = action.pop("start_block")
                while startBlock and startBlock >= self.blockNumber:
                    if self.blockNumber >= self.scenarios[self.scenariosNr]["scenario_blocks"]:
                        return
                    time.sleep(0.1)
                if self.blockNumber >= self.scenarios[self.scenariosNr]["scenario_blocks"]:
                    return

                self.eos_rpc.push_action(action)
        else:
            print("There are no actions.")


