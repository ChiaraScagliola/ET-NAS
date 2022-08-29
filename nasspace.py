from models import get_cell_based_tiny_net, get_search_spaces
#from nas_201_api import NASBench201API as API
#from nasbench import api as nasbench101api
#from nas_101_api.model import Network
#from nas_101_api.model_spec import ModelSpec
import itertools
import random
import numpy as np
from models.cell_searchs.genotypes import Structure
from copy import deepcopy
from pycls.models.nas.nas import NetworkImageNet, NetworkCIFAR
from pycls.models.anynet import AnyNet
from pycls.models.nas.genotypes import GENOTYPES, Genotype
import json
import torch
from nats_bench import create
from timeit import default_timer as timer
#import xautodl 
import ast
from nats_bench.genotype_utils import topology_str2structure
 # import this lib -- "https://github.com/D-X-Y/AutoDL-Projects", you can use pip install xautodl
#from xautodl.models import get_cell_based_tiny_net


class Nasbench:
    def __init__(self, dataset, df_conf):
        self.dataset = dataset
        self.df_conf = df_conf
        #self.api = API(apiloc, verbose=False)
        self.api = create(None, 'tss', fast_mode=True, verbose=False)
        self.epochs = '12'
    def get_network(self, uid):
        #config = self.api.get_net_config(uid, 'cifar10-valid')
        #config['num_classes'] = 1
        config = ast.literal_eval(self.df_conf[uid])
        if self.dataset == 'ImageNet16-120':
          config['num_classes'] = 120
        if self.dataset == 'cifar100':
          config['num_classes'] = 100
        else:
          config['num_classes'] = 10
               
        network = get_cell_based_tiny_net(config)
        #network.apply(init)
        return network
    def get_str(self, uid):
        return ast.literal_eval(self.df_conf[uid])['arch_str']

    def NNDegree(searchspace, uid):

      strOp = searchspace.get_str(uid)
      listOp = strOp.split('|')
      id = [1,4,8]
      nConv = strOp.count('conv')
      skip1 = [3,7]
      skip2 = [6]
      nID = ''.join([i for j, i in enumerate(listOp) if j in id]).count('skip')
      nS1 = ''.join([i for j, i in enumerate(listOp) if j in skip1]).count('skip')
      nS2  = ''.join([i for j, i in enumerate(listOp) if j in skip2]).count('skip')
      nNone = strOp.count('none')
      #skip = searchspace.get_unique_str(uid).count('skip')
      Sc = (nS1+2*nS2)
      Wc = nConv
      return int((Wc + Sc))
      
    def get_unique_str(self, uid):
        arch_str = ast.literal_eval(self.df_conf[uid])['arch_str']
        structure = topology_str2structure(arch_str)
        return structure.to_unique_str(consider_zero=True)
    def get_list(self, uid):
        return self.api.str2lists(self.get_str(uid))
    def __iter__(self):
        for uid in range(len(self)):
            network = self.get_network(uid)
            yield uid, network
    def __getitem__(self, index):
        return index
    def __len__(self):
        return 15625
    def num_activations(self):
        network = self.get_network(0)
        return network.classifier.in_features
    #def get_12epoch_accuracy(self, uid, acc_type, trainval, traincifar10=False):
    #    archinfo = self.api.query_meta_info_by_index(uid)
    #    if (self.dataset == 'cifar10' or traincifar10) and trainval:
    #        #return archinfo.get_metrics('cifar10-valid', acc_type, iepoch=12)['accuracy']
    #        return archinfo.get_metrics('cifar10-valid', 'x-valid', iepoch=12)['accuracy']
    #    elif traincifar10:
    #        return archinfo.get_metrics('cifar10', acc_type, iepoch=12)['accuracy']
    #    else:
    #        return archinfo.get_metrics(self.dataset, 'ori-test', iepoch=12)['accuracy']
    def get_12epoch_accuracy(self, uid, acc_type, trainval, traincifar10=False):
        #archinfo = self.api.query_meta_info_by_index(uid)
        #if (self.dataset == 'cifar10' and trainval) or traincifar10:
        info = self.api.get_more_info(uid, 'cifar10-valid', iepoch=None, hp=self.epochs, is_random=True)
        #else:
        #    info = self.api.get_more_info(uid, self.dataset, iepoch=None, hp=self.epochs, is_random=True)
        return info['valid-accuracy']
    def get_final_accuracy(self, uid):
        info = self.api.get_more_info(uid, self.dataset, iepoch=None, hp='200', is_random=False)
        return info['test-accuracy']


    def get_accuracy(self, uid, acc_type, trainval=True):
        archinfo = self.api.query_meta_info_by_index(uid)
        if self.dataset == 'cifar10' and trainval:
            return archinfo.get_metrics('cifar10-valid', acc_type)['accuracy']
        else:
            return archinfo.get_metrics(self.dataset, acc_type)['accuracy']

    def get_accuracy_for_all_datasets(self, uid):
        archinfo = self.api.query_meta_info_by_index(uid,hp='200')

        c10 = archinfo.get_metrics('cifar10', 'ori-test')['accuracy']
        c10_val = archinfo.get_metrics('cifar10-valid', 'x-valid')['accuracy']

        c100 = archinfo.get_metrics('cifar100', 'x-test')['accuracy']
        c100_val = archinfo.get_metrics('cifar100', 'x-valid')['accuracy']

        imagenet = archinfo.get_metrics('ImageNet16-120', 'x-test')['accuracy']
        imagenet_val = archinfo.get_metrics('ImageNet16-120', 'x-valid')['accuracy']

        return c10, c10_val, c100, c100_val, imagenet, imagenet_val

    #def train_and_eval(self, arch, dataname, acc_type, trainval=True):
    #    unique_hash = self.__getitem__(arch)
    #    time = self.get_training_time(unique_hash)
    #    acc12 = self.get_12epoch_accuracy(unique_hash, acc_type, trainval)
    #    acc = self.get_final_accuracy(unique_hash, acc_type, trainval)
    #    return acc12, acc, time
    def train_and_eval(self, arch, dataname, acc_type, trainval=True, traincifar10=False):
        unique_hash = self.__getitem__(arch)
        time = self.get_training_time(unique_hash)
        acc12 = self.get_12epoch_accuracy(unique_hash, acc_type, trainval, traincifar10)
        acc = self.get_final_accuracy(unique_hash, acc_type, trainval)
        return acc12, acc, time
    def random_arch(self):
        return random.randint(0, len(self)-1)
    def get_training_time(self, unique_hash):
        info = self.api.get_more_info(unique_hash, 'cifar10-valid' if self.dataset == 'cifar10' else self.dataset, iepoch=None,hp=12, is_random=True)

        #info = self.api.get_more_info(unique_hash, 'cifar10-valid', iepoch=None, use_12epochs_result=True, is_random=True)
        #info = self.api.get_more_info(unique_hash, 'cifar10-valid', iepoch=None, hp='12', is_random=True)
        return info['train-all-time'] + info['valid-per-time']
        #if self.dataset == 'cifar10' and trainval:
        #    info = self.api.get_more_info(unique_hash, 'cifar10-valid', iepoch=None, hp=self.epochs, is_random=True)
        #else:
        #    info = self.api.get_more_info(unique_hash, self.dataset, iepoch=None, hp=self.epochs, is_random=True)

        ##info = self.api.get_more_info(unique_hash, 'cifar10-valid', iepoch=None, use_12epochs_result=True, is_random=True)
        #return info['train-all-time'] + info['valid-per-time']
    def mutate_arch(self, arch):
        op_names = get_search_spaces('cell', 'nas-bench-201')
        config = self.api.get_net_config(arch, self.dataset)
        #config = self.api.get_net_config(arch, 'cifar10-valid')
        parent_arch = Structure(self.api.str2lists(config['arch_str']))
        child_arch = deepcopy( parent_arch )
        node_id = random.randint(0, len(child_arch.nodes)-1)
        node_info = list( child_arch.nodes[node_id] )
        snode_id = random.randint(0, len(node_info)-1)
        xop = random.choice( op_names )
        while xop == node_info[snode_id][0]:
          xop = random.choice( op_names )
        node_info[snode_id] = (xop, node_info[snode_id][1])
        child_arch.nodes[node_id] = tuple( node_info )
        arch_index = self.api.query_index_by_arch( child_arch )
        return arch_index

class Nasbench101:
    def __init__(self, dataset, apiloc, args):
        self.dataset = dataset
        self.api = nasbench101api.NASBench(apiloc)
        self.args = args
    def get_accuracy(self, unique_hash, acc_type, trainval=True):
        spec = self.get_spec(unique_hash)
        _, stats = self.api.get_metrics_from_spec(spec)
        maxacc = 0.
        for ep in stats:
            for statmap in stats[ep]:
                newacc = statmap['final_test_accuracy']
                if newacc > maxacc:
                    maxacc = newacc
        return maxacc
    def get_final_accuracy(self, uid, acc_type, trainval):
        return self.get_accuracy(uid, acc_type, trainval)
    def get_training_time(self, unique_hash):
        spec = self.get_spec(unique_hash)
        _, stats = self.api.get_metrics_from_spec(spec)
        maxacc = -1.
        maxtime = 0.
        for ep in stats:
            for statmap in stats[ep]:
                newacc = statmap['final_test_accuracy']
                if newacc > maxacc:
                    maxacc = newacc
                    maxtime = statmap['final_training_time']
        return maxtime
    def get_network(self, unique_hash):
        spec = self.get_spec(unique_hash)
        network = Network(spec, self.args)
        return network
    def get_spec(self, unique_hash):
        matrix = self.api.fixed_statistics[unique_hash]['module_adjacency']
        operations = self.api.fixed_statistics[unique_hash]['module_operations']
        spec = ModelSpec(matrix, operations)
        return spec
    def __iter__(self):
        for unique_hash in self.api.hash_iterator():
            network = self.get_network(unique_hash)
            yield unique_hash, network
    def __getitem__(self, index):
        return next(itertools.islice(self.api.hash_iterator(), index, None))
    def __len__(self):
        return len(self.api.hash_iterator())
    def num_activations(self):
        for unique_hash in self.api.hash_iterator():
            network = self.get_network(unique_hash)
            return network.classifier.in_features
    def train_and_eval(self, arch, dataname, acc_type, trainval=True, traincifar10=False):
        unique_hash = self.__getitem__(arch)
        time =12.* self.get_training_time(unique_hash)/108.
        acc = self.get_accuracy(unique_hash, acc_type, trainval)
        return acc, acc, time
    def random_arch(self):
        return random.randint(0, len(self)-1)
    def mutate_arch(self, arch):
        unique_hash = self.__getitem__(arch)
        matrix = self.api.fixed_statistics[unique_hash]['module_adjacency']
        operations = self.api.fixed_statistics[unique_hash]['module_operations']
        coords = [ (i, j) for i in range(matrix.shape[0]) for j in range(i+1, matrix.shape[1])]
        random.shuffle(coords)
        # loop through changes until we find change thats allowed
        for i, j in coords:
            # try the ops in a particular order
            for k in [m for m in np.unique(matrix) if m != matrix[i, j]]:
                newmatrix = matrix.copy()
                newmatrix[i, j] = k
                spec = ModelSpec(newmatrix, operations)
                try:
                    newhash = self.api._hash_spec(spec)
                    if newhash in self.api.fixed_statistics:
                        return [n for n, m in enumerate(self.api.fixed_statistics.keys()) if m == newhash][0]
                except:
                    pass




class ReturnFeatureLayer(torch.nn.Module):
    def __init__(self, mod):
        super(ReturnFeatureLayer, self).__init__()
        self.mod = mod
    def forward(self, x):
        return self.mod(x), x
                

def return_feature_layer(network, prefix=''):
    #for attr_str in dir(network):
    #    target_attr = getattr(network, attr_str)
    #    if isinstance(target_attr, torch.nn.Linear):
    #        setattr(network, attr_str, ReturnFeatureLayer(target_attr))
    for n, ch in list(network.named_children()):
        if isinstance(ch, torch.nn.Linear):
            setattr(network, n, ReturnFeatureLayer(ch))
        else:
            return_feature_layer(ch, prefix + '\t')
             

class NDS:
    def __init__(self, searchspace):
        self.searchspace = searchspace
        data = json.load(open(f'nds_data/{searchspace}.json', 'r'))
        try:
            data = data['top'] + data['mid']
        except Exception as e:
            pass
        self.data = data
    def __iter__(self):
        for unique_hash in range(len(self)):
            network = self.get_network(unique_hash)
            yield unique_hash, network
    def get_network_config(self, uid):
        return self.data[uid]['net']
    def get_network_optim_config(self, uid):
        return self.data[uid]['optim']
    def get_network(self, uid):
        netinfo = self.data[uid]
        config = netinfo['net']
        #print(config)
        if 'genotype' in config:
            #print('geno')
            gen = config['genotype']
            genotype = Genotype(normal=gen['normal'], normal_concat=gen['normal_concat'], reduce=gen['reduce'], reduce_concat=gen['reduce_concat'])
            if '_in' in self.searchspace:
                network = NetworkImageNet(config['width'], 1, config['depth'], config['aux'],  genotype)
            else:
                network = NetworkCIFAR(config['width'], 1, config['depth'], config['aux'],  genotype)
            network.drop_path_prob = 0.
            #print(config)
            #print('genotype')
            L = config['depth']
        else:
            if 'bot_muls' in config and 'bms' not in config:
                config['bms'] = config['bot_muls']
                del config['bot_muls']
            if 'num_gs' in config and 'gws' not in config:
                config['gws'] = config['num_gs']
                del config['num_gs']
            config['nc'] = 1
            config['se_r'] = None
            config['stem_w'] = 12
            L = sum(config['ds'])
            if 'ResN' in self.searchspace:
                config['stem_type'] = 'res_stem_in'
            else:
                config['stem_type'] = 'simple_stem_in'
            #"res_stem_cifar": ResStemCifar,
            #"res_stem_in": ResStemIN,
            #"simple_stem_in": SimpleStemIN,
            if config['block_type'] == 'double_plain_block':
                config['block_type'] = 'vanilla_block'
            network = AnyNet(**config)
        return_feature_layer(network)
        return network
    def __getitem__(self, index):
        return index
    def __len__(self):
        return len(self.data)
    def random_arch(self):
        return random.randint(0, len(self.data)-1)
    def get_final_accuracy(self, uid, acc_type, trainval):
        return 100.-self.data[uid]['test_ep_top1'][-1]


def get_search_space(dataset, df_conf):
    return Nasbench(dataset, df_conf)
    