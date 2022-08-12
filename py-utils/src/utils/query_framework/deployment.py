#!/usr/bin/env python3

# CORTX-Py-Utils: CORTX Python common library.
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import os
import json
import errno
from collections import defaultdict
from cortx.utils.conf_store import Conf
from cortx.utils.conf_store import ConfStore
from cortx.utils.query_framework.error import DeploymentConfigError
from cortx.utils.query_framework import const

class DeploymentConfig:
    def __init__(self):
        self._query_idx = "query_idx"
        self._data_idx = "data_idx"
        self._local_file = "/tmp/local_conf.conf"
        self._local_conf = "yaml://" + self._local_file
        self.topology=const.TOPOLOGY

    def get_data(self, kv_url: str):
        """Get data related to the parent key from config."""
        return self._get_data(kv_url)

    def _get_data(self, kv_url: str):
        """Return data in dict format."""
        try:
            Conf.load(self._query_idx, kv_url)
        except:
            pass
        _data_keys = Conf.get_keys(self._query_idx)
        try:
            Conf.load(self._data_idx, self._local_conf)
        except:
            pass
        Conf.copy(self._query_idx, self._data_idx, _data_keys)
        Conf.save(self._data_idx)
        for key in Conf.get_keys(self._data_idx):
            if 'num_'in key:
                Conf.delete(self._data_idx, key)
        Conf.save(self._data_idx)
        _cs = ConfStore()
        _cs.load(self._data_idx,  self._local_conf)
        _data = _cs.get_data(self._data_idx)
        return _data.get_data() 
    
class DeploymentTopology():
    _query_conf = None
    def __init__(self):
        """ Static init for initialising and setting attributes."""
        if self._query_conf is None:
            self._query_conf = DeploymentConfig()

    @staticmethod
    def get_cortx_topology(kv_url: str) -> dict:
        """ get cluster toplogy """
        _data = {}
        _data = DeploymentTopology._query_conf.get_data(kv_url)
        if not len(_data) > 0:
            raise DeploymentTopologyError(errno.EINVAL, f"Invalid data in {kv_url}")
        return DeploymentTopology._get_cortx_topology(_data)
    @staticmethod
    def _get_cortx_topology(data: dict) -> dict:
        """ Map gconf fields to topology """
        nested_dict = lambda: defaultdict(nested_dict)
        topology_obj = DeploymentConfig()
        _config = topology_obj.topology

        # To fetch common_info
        _config["cortx"]["common"]["release"] = data['cortx']['common']['release']

        # To fetch cluster_info
        cluster_info = nested_dict()
        for cluster_key, cluster_val in data['cluster'].items():
            storage_set_info = nested_dict()
            storage_set_list=[]
            cluster_info['security'] = data['cortx']['common']['security']
            if cluster_key == 'storage_set':
                for storage_info in data['cluster']['storage_set']:
                    for storage_key,storage_val in storage_info.items():
                        if storage_key != 'nodes':
                            storage_set_info[storage_key] = storage_val
                storage_set_list.append(storage_set_info)
                cluster_info['storage_set'] = storage_set_list
            else:
                cluster_info[cluster_key] = cluster_val
        _config['cluster'].append((json.loads(json.dumps(cluster_info))))

        # To fetch Nodes Info
        for nodes_key in data['node'].keys():
            nodes_info = nested_dict()
            nodes_info['machine_id'] = nodes_key
            for key, val in data['node'][nodes_key].items():
                if key == 'provisioning':
                    nodes_info['deployment_time'] = data['node'][nodes_key]['provisioning']['time']
                    nodes_info['version'] = data['node'][nodes_key]['provisioning']['version']
                else:
                    nodes_info[key] = val
            _config["nodes"].append(json.loads(json.dumps(nodes_info)))
        if os.path.exists(DeploymentConfig._local_file):
            os.remove(DeploymentConfig._local_file)
        del topology_obj
        return _config
