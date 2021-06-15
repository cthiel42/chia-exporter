import json
import time
import requests
from prometheus_client import start_http_server, REGISTRY, Metric
from pathlib import Path
import asyncio
from bs4 import BeautifulSoup

import sys

sys.path.append("/opt/chia-blockchain")

from chia.util.config import load_config
from chia.rpc.full_node_rpc_client import FullNodeRpcClient
from chia.rpc.harvester_rpc_client import HarvesterRpcClient
from chia.rpc.wallet_rpc_client import WalletRpcClient

class Collector(object):
    def __init__(self, config):
        self.user_config = load_user_config()
        self.config = load_config(Path("/root/.chia/mainnet"), "config.yaml")

    def collect(self):
        start = time.time()
        print("Running Collection")
        processes = []
        for path in self.user_config["metrics"]:
            if hasattr(self, path):
                method = getattr(self, path)
                metrics = asyncio.run(asyncio.coroutine(method)())
                if metrics==None:
                    continue
                for metric in metrics:
                    yield metric

        print("Collection complete in: "+str(time.time()-start)+" seconds")

    async def get_blockchain_state(self):
        name = "get_blockchain_state"
        start = time.time()
        print(name+": Starting")
        
        client = await FullNodeRpcClient.create("host.docker.internal",8555,Path("/root/.chia/mainnet"),self.config)
        results = await client.get_blockchain_state()
        client.close()
        
        metric1 = Metric('chia_network_size',"Network size in bytes","summary")
        metric1.add_sample('chia_network_size',value=results["space"],labels={})
        metric2 = Metric('chia_network_difficulty',"Network difficulty","summary")
        metric2.add_sample('chia_network_difficulty',value=results["difficulty"],labels={})
        metric3 = Metric('chia_is_node_synced',"Is Node Synced To Blockchain","summary")
        node_synced = 0
        if results["sync"]["synced"] == True:
            node_synced = 1
        metric3.add_sample('chia_is_node_synced',value=node_synced,labels={})
        
        print(name+": Done in "+str(time.time()-start)+" seconds")
        return [metric1,metric2,metric3]

    async def get_wallet_balance(self):
        name = "get_wallet_balance"
        start = time.time()
        print(name+": Starting")

        client = await WalletRpcClient.create("host.docker.internal",9256,Path("/root/.chia/mainnet"),self.config)
        wallets = await client.get_wallets()
        height_info = await client.get_height_info()

        metric1 = Metric('chia_wallet_balance',"Wallet balance","summary")
        for wallet in wallets:
            results = await client.get_wallet_balance(wallet["id"])
            metric1.add_sample('chia_wallet_balance',value=results["confirmed_wallet_balance"], labels={"wallet_id":str(wallet["id"])})

        metric2 = Metric('chia_wallet_height','Block Height of Chia Wallet','summary')
        metric2.add_sample('chia_wallet_height',value=height_info,labels={})
        
        client.close()

        print(name+": Done in "+str(time.time()-start)+" seconds")
        return [metric1,metric2]

    async def get_plots(self):
        name = "get_plots"
        start = time.time()
        print(name+": Starting")

        client = await HarvesterRpcClient.create("host.docker.internal",8560,Path("/root/.chia/mainnet"),self.config)
        results = await client.get_plots()
        client.close()
        metric1 = Metric('chia_plot_count_sum',"Sum of plots on machine","summary")
        metric1.add_sample('chia_plot_count_sum',value=len(results["plots"]), labels={})
        plot_size = 0
        for plot in results["plots"]:
            plot_size += plot["file_size"]
        metric2 = Metric('chia_plot_size_sum',"Sum of plot size in bytes","summary")
        metric2.add_sample('chia_plot_size_sum',value=plot_size, labels={})

        print(name+": Done in "+str(time.time()-start)+" seconds")
        return [metric1,metric2]

    async def get_pricing(self):
        name = "get_pricing"
        start = time.time()
        print(name+": Starting")

        try:
            resp = requests.get("https://coinmarketcap.com/currencies/chia-network/")
            soup = BeautifulSoup(resp.content, features="lxml")
            usd_price = float(soup.find_all("div",class_="priceValue___11gHJ")[0].text[1:].replace(",",""))
            vol_24hr = float(soup.find_all("div",class_="statsValue___2iaoZ")[2].text[1:].replace(",",""))    

            metric1 = Metric('chia_usd_price','Chia USD Price',"summary")
            metric1.add_sample('chia_usd_price',value=usd_price,labels={})
            metric2 = Metric('chia_24hr_volume_usd','Chia 24 Hour Volume Traded',"summary")
            metric2.add_sample('chia_24hr_volume_usd',value=vol_24hr,labels={})
        except Exception as e:
            print(name+": Failed to run. Error follows")
            print(e)
            return []

        print(name+": Done in "+str(time.time()-start)+" seconds")
        return [metric1,metric2]

def load_user_config():
    try:
        configFile = open("config.json","r")
        config = json.loads(configFile.read())
        configFile.close()
    except Exception as e:
        config["port"] = 9101
        config["metrics"] = ["get_blockchain_state","get_wallet_balance","get_plots","get_pricing"]
    
    if "port" not in config:
        config["port"] = 9101
    if "metrics" not in config:
        config["metrics"] = ["get_blockchain_state","get_wallet_balance","get_plots","get_pricing"]
    
    return config
    
def main():
    user_config = load_user_config()
    
    start_http_server(user_config["port"])

    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    REGISTRY.register(Collector({}))

    print("Exporter Running")
    while 1:
        time.sleep(5)

main()
