import hashlib
import json
from time import time
from uuid import uuid4
from urllib.parse import urlparse
import random
from flask import Flask, jsonify, request
import string

class BlockChain(object):
    """ Main BlockChain class """
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()
        # create the genesis block
        self.new_block(previous_hash=1, proof=100)

    @staticmethod
    def hash(block):
        # hashes a block
        # also make sure that the transactions are ordered otherwise we will have insonsistent hashes!
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def new_block(self, proof, previous_hash=None):
        # creates a new block in the blockchain
        block = {
            'index': len(self.chain)+1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # reset the current list of transactions
        self.current_transactions = []
        self.chain.append(block)
        return block

    @property
    def last_block(self):
        # returns last block in the chain
        return self.chain[-1]

    def new_transaction(self, sender, recipient, amount):
        # adds a new transaction into the list of transactions
        # these transactions go into the next mined block
        self.current_transactions.append({
            "sender":sender,
            "recient":recipient,
            "amount":amount,
        })
        return int(self.last_block['index'])+1

    def proof_of_work(self, last_proof):
        # simple proof of work algorithm
        # find a number p' such as hash(pp') containing leading 4 zeros where p is the previous p'
        # p is the previous proof and p' is the new proof
        proof = 0
        while self.validate_proof(last_proof, proof) is False:
            proof += 1
        return proof

    @staticmethod
    def validate_proof(last_proof, proof):
        # validates the proof: does hash(last_proof, proof) contain 4 leading zeroes?
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def register_node(self, address):
        # add a new node to the list of nodes
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def full_chain(self):
        # xxx returns the full chain and a number of blocks
        pass

# initiate the node
app = Flask(__name__)
# generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')
# initiate the Blockchain
blockchain = BlockChain()

@app.route('/mine/<wallet_adress>', methods=['GET'])
def mine(wallet_adress):

    # first we need to run the proof of work algorithm to calculate the new proof..
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    json_file = open("wallets.json")
    variables = json.load(json_file)
    if wallet_adress in variables:
        with open('wallets.json', 'r') as f:
            wallet_bals = json.load(f)
        mining_rewards = wallet_bals
        mining_rewardnum = mining_rewards['MiningWallet']
        mining_reward = random.randint(0,mining_rewardnum)
        if mining_reward > 5:
            mining_reward = random.randint(0,5)
        if mining_rewardnum <= 5:
            return "There is not currently enough coins in the mining wallet to give out a reward to a miner (you), make a large transaction or wait for someone else to do the same for more to be added..."
        adder = wallet_bals
        adder[wallet_adress] = int(adder[wallet_adress]) + int(mining_reward)
        adder['MiningWallet'] = int(adder['MiningWallet']) - int(mining_reward)
        with open('wallets.json', 'r+') as f:
            json.dump(adder, f, indent=4)
    else:
        return "wallet does not exist!"
    json_file.close()

    # we must recieve reward for finding the proof in form of receiving 1 Coin
    blockchain.new_transaction(
        sender="Mining Rewards",
        recipient=wallet_adress,
        amount=mining_reward,
    )

    # forge the new block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "Forged new block.",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response, 200)


def percent(expression):
    if "%" in expression:
        expression = expression.replace("%","/100")
    return eval(expression)


@app.route('/transaction/new/<frm>/<key>/<to>/<amount>', methods=['GET'])
def new_transaction(frm, key, to, amount):


    if frm == 'MiningWallet':
        return 'You cannot make or attempt to make a Transaction from the mining wallet, i know you thought you were smart!'
    else:
        pass

    # create a new transaction
    key_file = open("keys.json")
    keys = json.load(key_file)
    walletkey = keys[frm]
    with open('wallets.json', 'r') as f:
        wallet_bals = json.load(f)

    tax = percent(f"{amount}*10%")
    if amount >= 80000000:
        return "Transactions of this size are not allowed, max size is 70000000 ECN with a network fee of 20% due to the larger size."
    if amount >= 70000000:
        tax = percent(f"{amount}*20%")
    required_amount = int(amount) + tax
    if int(wallet_bals[frm]) < int(required_amount):
        return 'balance is insufficient!, this may be because of the network fee, the required balance for this transaction is: ' + str(required_amount)
    if key != walletkey:
        return '[ERROR CODE: BABY PORG]: that not the right private key stop trying to be a big haxor boi!, if you are the owner of the account you are trying to send funds from and you have lost your private key, sorry there is nothing we can do at this time...'
    else:
        adder = wallet_bals
        adder[to] = int(adder[to]) + int(amount)
        adder[frm] = int(adder[frm]) - int(required_amount)
        adder['MiningWallet'] = int(adder['MiningWallet']) + int(tax)
        with open('wallets.json', 'w') as f:
            json.dump(adder, f, indent=4)
        pass
        index = blockchain.new_transaction(
            sender = frm,
            recipient = to,
            amount = amount
        )

    response = {
        'message': f'Transaction Completed {amount} Sent To: {to} Amount Paid In Total (with network fee): {required_amount} Transaction will be added to the Block {index}.',
    }
    return jsonify(response, 200)

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    print('values',values)
    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    # register each newly added node
    for node in nodes: blockchain.register_node(node)

    response = {
        'message': "New nodes have been added",
        'all_nodes': list(blockchain.nodes),
    }

    return jsonify(response), 201

@app.route('/wallet/new', methods=['GET'])
def newWallet():
        letters = string.ascii_letters
        wallet = ('ECN' + ''.join(random.choice(letters) for i in range(32)))
        private_key = (''.join([random.choice(string.ascii_letters + string.digits) for n in range(50)]))
        # function to add to JSON
        with open('wallets.json','r+') as f:
            wallets = json.load(f)

        wallets[wallet] = 0
        with open('wallets.json','r+') as f:
            json.dump(wallets, f, indent=4)
        with open('keys.json', 'r+') as f:
            keys = json.load(f)
        keys[wallet] = private_key
        with open('keys.json', 'r+') as f:
            json.dump(keys, f, indent=4)

        return "a new wallet has been generated its adress is: || " + wallet + " || and the private key is: || " + private_key + " || DO NOT LOSE THIS KEY AS IF YOU LOSE IT YOU CAN NOT GET YOUR WALLET BACK!"


@app.route('/getwalletbal/<walletadress>', methods=['GET'])
def getwallet(walletadress):
    json_file = open("wallets.json")
    variables = json.load(json_file)
    if walletadress in variables:
        return "wallets balance is: " + str(variables[walletadress])
    else:
        return "wallet does not exist!"
    json_file.close()


@app.route('/', methods=['GET'])
def index_url():
    return """
    <body style="background-color:grey;">
    urls are:
    <br>
    /mine/walletadress // request must be a get request just mines a block can be spam requested for quicker mining.
    <br>
    /getwalletbal/walletadress // returns the global wallet value
    <br>
    /transaction/new/senderwalletadress/senderwalletprivatekey/recieveradress/amount/ // get request so can be done in browser
    <br>
    /chain // get request and returns the current full blockchain
    <br>
    /nodes/register // post request with the value(s) nodes definied.
    <br>
    /wallet/new // creates a new wallet with 0 ECN get request, returns wallet adress and wallet private key save both in something like a .txt file
    </body>
    """


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)


