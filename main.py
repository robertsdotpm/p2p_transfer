import storjnode
from storjnode.network import DEFAULT_BOOTSTRAP_NODES
from storjnode.network.file_transfer import FileTransfer
from storjnode.network.process_transfers import process_transfers
from storjnode.util import address_to_node_id
from storjnode.network.bandwidth.limit import BandwidthLimit
from storjnode.config import ConfigFile
import btctxstore
import pyp2p
import hashlib
import tempfile
import os
import time
import requests
import unittest
import shutil
from crochet import setup
setup()
from os import listdir
from os.path import isfile, join
from threading import Thread

print("")
print("------- P2P File Sharing ------")
print("")

print("")
print("Starting DHT and Networking ... Please wait")
print("")

test_storage_dir = tempfile.mkdtemp()

# Sample node.
wallet = btctxstore.BtcTxStore(testnet=False, dryrun=True)
wif = wallet.get_key(wallet.create_wallet())
node_id = address_to_node_id(wallet.get_address(wif))
store_config = {
    os.path.join(test_storage_dir, "storage"): {"limit": 0}
}

dht_node = storjnode.network.Node(
    wif, bootstrap_nodes=DEFAULT_BOOTSTRAP_NODES,
    disable_data_transfer=True
)

# Transfer client.
client = FileTransfer(
    pyp2p.net.Net(
        net_type="direct",
        passive_port=0,
        dht_node=dht_node,
        debug=1
    ),
    BandwidthLimit(),
    wif=wif,
    store_config=store_config
)

# Accept all transfers.
def accept_handler(contract_id, src_unl, data_id, file_size):
    return 1

# Add accept handler.
client.handlers["accept"].add(accept_handler)

def completion_handler(success_value, contract_id=None, con=None):
    sending_data = False
    print("")
    print("Transfer complete")
    print("Look in (if downloading): " + str(test_storage_dir))
    print("")

# Add completion handler.
client.add_handler("complete", completion_handler)

# Process file transfers.
sending_data = True
def process_transfer_thread():
    while sending_data:
        process_transfers(client)
        time.sleep(0.002)

Thread(target=process_transfer_thread).start()

print("waiting for net to be stable")
time.sleep(storjnode.network.WALK_TIMEOUT)
dht_node.refresh_neighbours()
time.sleep(storjnode.network.WALK_TIMEOUT)

print("")
print("Our UNL = " + client.net.unl.value)
print("Give this to someone else to connect to")
print("")

print("")
print("Enter the UNL of a remote peer to share files with")
print("or simply wait to receive a connection")
print("")
dest_unl = raw_input("Destination UNL: ")


print("")
print("Select file in current directory to upload")
print("or simply wait to receive a file from another peer.")
print("")

file_list = []
index = 0
for f in listdir("."):
    if isfile(join(".", f)):
        file_list.append(f)
        print("[%d] %s" % (index, f))
        index += 1

print("")
index = int(raw_input("Choice: "))
choice = os.path.abspath(join(".", file_list[index]))

print("Upload in progress ... please wait")

# Move file to storage directory.
path = choice
file_info = client.move_file_to_storage(path)

# Tell them to download our file.
contract_id = client.data_request(
    "download",
    file_info["data_id"],
    0,
    dest_unl
)

# Wait for transfer to finish.
d = client.defers[contract_id]

def failure_handler(failure_value):
    sending_data = False
    print("")
    print("Transfer failed")
    print(failure_value)
    print("")

d.addErrback(failure_handler)

while sending_data:
    time.sleep(1)

raw_input("Press enter to exit . . .")
client.stop()
