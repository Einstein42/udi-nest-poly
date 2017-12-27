#!/usr/bin/env python
"""
Nest NodeServer for UDI Polyglot v2
by Einstein.42 (James Milne) milne.james@gmail.com
"""

import polyinterface
import sys
import json
import nest
from os.path import join, expanduser
import requests

LOGGER = polyinterface.LOGGER
SERVERDATA = json.load(open('server.json'))
VERSION = SERVERDATA['credits'][0]['version']
NEST_STATES = {0: "off", 1: "heat", 2: "cool", 3: "heat-cool", 13: "away"}

def myfloat(value, prec=2):
    """ round and return float """
    return round(float(value), prec)

def temp(value):
    pass

# These are specific to e42's implemntation of this NodeServer at developer.nest.com.
# If you have your own Nest developer account, feel free to use your own.
PRODUCTID = '7246c000-8590-4d79-960d-71c1f6f47133'
PRODUCTSECRET = 'GrjzLXLmwAylG2dvhs0LpzEiN'
CACHEFILE = join(expanduser("~") + '/.polyglot/.nest_auth')
PRODUCTVER = 2

class Controller(polyinterface.Controller):
    def __init__(self, polyglot):
        super(Controller, self).__init__(polyglot)
        self.name = 'Nest Controller'
        self.napi = None

    def start(self):
        LOGGER.info('Starting Nest Polyglot v2 NodeServer version {}'.format(VERSION))
        self.napi = nest.Nest(client_id=PRODUCTID, client_secret=PRODUCTSECRET, access_token_cache_file=CACHEFILE, cache_ttl=25)
        if self.napi.authorization_required:
            try:
                LOGGER.debug(self.polyConfig['customParams']['pin'])
                self.napi.request_token(self.polyConfig['customParams']['pin'])
                LOGGER.info('PIN Found in config. Requesting Token.')
                self.discover()
            except (AttributeError, KeyError):
                LOGGER.info('Go to {} to authorize. Then enter the code under the Custom Parameters section. Create '.format(self.napi.authorize_url) + \
                        'a key called "pin" with the code as the value, then restart the NodeServer.')
        else:
            self.discover()

    def longPoll(self):
        for node in self.nodes:
            self.nodes[node].update()

    def update(self):
        """
        Nothing to update for the controller.
        """
        pass

    def discover(self, command = None):
        LOGGER.info('Discovering Nest Products...')
        for structure in self.napi.structures:
            LOGGER.info('Structure found: {}'.format(structure.name))
            for device in structure.thermostats:
                LOGGER.info('Found Thermostat: {} with Serial Number: {}'.format(device.name, device.serial))
                address = device.serial[:14].replace('-', '').replace('_', '').lower()
                if address not in self.nodes:
                    self.addNode(Thermostat(self, self.address, address, device.name, device))
                else:
                    LOGGER.info('Thermostat: {} already configured. Skipping.'.format(device.name))

    commands = {'DISCOVER': discover}

class Thermostat(polyinterface.Node):
    def __init__(self, parent, primary, address, name, device):
        self.device = device
        self.structure = device.structure
        #LOGGER.debug(self.device.temperature_scale)
        LOGGER.info('Nest Thermostat: {}@{} Current Ambient Temp: {}'\
                    .format(self.device.name, self.structure.name, self.device.temperature))
        super(Thermostat, self).__init__(parent, primary, address, '{}'.format(name))
        self.away = False
        self.online = True
        self.mode = None
        self.humidity = None
        self.state = None
        self.insidetemp = None

    def start(self):
        LOGGER.info("{} ready to control!".format(self.name))
        self.update()

    def update(self):
        try:
            if self._checkconnect():
                if self.structure.away == "away":
                    self.away = True
                else:
                    self.away = False
                self.mode = self.device.mode
                if self.away:
                    self.setDriver('CLIMD', '13')
                elif self.mode == 'heat-cool':
                    self.setDriver('CLIMD', '3')
                elif self.mode == 'heat':
                    self.setDriver('CLIMD', '1')
                elif self.mode == 'cool':
                    self.setDriver('CLIMD', '2')
                elif self.mode == 'fan':
                    self.setDriver('CLIMD', '6')
                else:
                    self.setDriver('CLIMD', '0')
                self.setDriver('CLIFS', 7 if self.device.fan else 8)
                self.online = self.device.online
                self.setDriver('GV4', 1 if self.online else 0)
                self.humidity = self.device.humidity
                self.setDriver('CLIHUM', self.humidity)
                if self.device.hvac_state == 'cooling':
                    self.state = '2'
                elif self.device.hvac_state == 'heating':
                    self.state = '1'
                else:
                    self.state = '0'
                self.setDriver('CLIHCS', self.state)
                self.insidetemp = self.device.temperature
                self.setDriver('ST', int(self.insidetemp))
                if self.mode == 'heat-cool':
                    self.targetlow = int(round(self.device.target[0]))
                    self.targethigh = int(round(self.device.target[1]))
                else:
                    self.targetlow = int(round(self.device.target))
                    #LOGGER.info('Target Temp is {}'.format(self.targetlow))
                    self.targethigh = self.targetlow
                self.setDriver('CLISPC', self.targethigh)
                self.setDriver('CLISPH', self.targetlow)
        except (requests.exceptions.HTTPError) as e:
            LOGGER.error('NestThermostat update Caught exception: %s', e)
        except:
            LOGGER.error('update Unexpected error: '.format(sys.exc_info()[0]))

    def query(self, command = None):
        self.update()
        self.reportDrivers()

    def _checkconnect(self):
        try:
            connected = self.device.online
            if not connected:
                self.parent.napi = nest.Nest(client_id=PRODUCTID, client_secret=PRODUCTSECRET, access_token_cache_file=CACHEFILE)
            return True
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, TypeError, requests.exceptions.ReadTimeout) as e:
            LOGGER.error('CheckConnect: %s', e)
            self.online = False
            self.setDriver('GV4', 0)

    def _setmode(self, command):
        try:
            val = command.get('value')
            if self._checkconnect():
                newstate = NEST_STATES[int(val)]
                LOGGER.info('Got mode change request from ISY. Setting Nest to: {}'.format(newstate))
                if newstate == 'away':
                    self.structure.away = True
                    self.away = True
                else:
                    self.structure.away = False
                    self.away = False
                    self.device.mode = newstate
                self.setDriver('CLIMD', int(val))
                #self.update_info()
        except (requests.exceptions.HTTPError) as e:
            LOGGER.error('NestThermostat _setmode Caught exception: %s', e)
        except:
            LOGGER.error('_setmode Unexpected error: '.format(sys.exc_info()[0]))

    def _setfan(self, command):
        try:
            val = int(command.get('value'))
            if self._checkconnect():
                if val == 1:
                    self.device.fan = True
                    LOGGER.info('Got Set Fan command. Setting fan to \'On\'')
                else:
                    self.device.fan = False
                    LOGGER.info('Got Set Fan command. Setting fan to \'Auto\'')
                self.setDriver('CLIFS', val)
        except (requests.exceptions.HTTPError) as e:
            LOGGER.error('NestThermostat SetFan Caught exception: %s', e)
        except:
            LOGGER.error('_setfan Unexpected error: '.format(sys.exc_info()[0]))

    def _sethigh(self, command):
        inc = False
        val = None
        try:
            val = int(command.get('value'))
        except TypeError:
            inc = True
        try:
            if self._checkconnect():
                if self.device.mode == 'heat-cool':
                    if not inc:
                        #self.device.temperature = (device.target[0], nest_utils.f_to_c(val))
                        self.device.temperature = (self.device.target[0], val)
                        LOGGER.info("Mode is heat-cool, Setting upper bound to {}".format(val))
                    else:
                        #val = int(nest_utils.c_to_f(device.target[1]) + 1)
                        val = int(self.device.target[1] + 1)
                        LOGGER.info("Mode is heat-cool, incrementing upper bound to {}".format(val))
                        self.device.temperature = (self.device.target[0], val)
                else:
                    if not inc:
                        self.device.temperature = int(val)
                    else:
                        val = int(self.device.target + 1)
                        self.device.temperature = val
                    LOGGER.info("Setting temperature to {}".format(val))
                self.setDriver('CLISPC', val)
        except (requests.exceptions.HTTPError) as e:
            LOGGER.error('NestThermostat _settemp Caught exception: %s', e)
        except:
            LOGGER.error('_sethigh Unexpected error: '.format(sys.exc_info()[0]))

    def _setlow(self, command):
        inc = False
        val = None
        try:
            val = int(command.get('value'))
        except TypeError:
            inc = True
        try:
            if self._checkconnect():
                if self.device.mode == 'heat-cool':
                    if not inc:
                        self.device.temperature = (val, self.device.target[1])
                        LOGGER.info("Mode is heat-cool, Setting lower bound to {}".format(val))
                    else:
                        val = int(round(self.device.target[0] - 1))
                        LOGGER.info("Mode is heat-cool, decrementing lower bound to {}".format(val))
                        self.device.temperature = (val, self.device.target[1])
                else:
                    if not inc:
                        self.device.temperature = val
                    else:
                        val = int(round(self.device.target - 1))
                        self.device.temperature = val
                    LOGGER.info("Setting temperature to {}".format(val))
                self.setDriver('CLISPH', val)
        except (requests.exceptions.HTTPError) as e:
            LOGGER.error('NestThermostat _settemp Caught exception: %s', e)
        except:
            LOGGER.error('_setlow Unexpected error: '.format(sys.exc_info()[0]))

    def _beep(self, command):
        LOGGER.info('Beep boop.')

    drivers = [{ 'driver': 'CLIMD', 'value': 0, 'uom': '67' },
                { 'driver': 'CLISPC', 'value': 0, 'uom': '14' },
                { 'driver': 'CLISPH', 'value': 0, 'uom': '14' },
                { 'driver': 'CLIFS', 'value': 0, 'uom': '99' },
                { 'driver': 'CLIHUM', 'value': 0, 'uom': '51' },
                { 'driver': 'CLIHCS', 'value': 0, 'uom': '66' },
                { 'driver': 'GV1', 'value': 0, 'uom': '14' },
                { 'driver': 'GV3', 'value': 0, 'uom': '14' },
                { 'driver': 'GV4', 'value': 0, 'uom': '2' },
                { 'driver': 'ST', 'value': 0, 'uom': '14' }]

    commands = {            'CLIMD': _setmode,
                            'CLIFS': _setfan,
                            'BRT': _sethigh,
                            'DIM': _setlow,
                            'BEEP': _beep,
                            'CLISPH': _setlow,
                            'CLISPC': _sethigh,
                            'QUERY': query}

    id = 'nestthermostat'

if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('Nest')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
