#
# Copyright (c) 2016 Nordic Semiconductor ASA
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this
#   list of conditions and the following disclaimer in the documentation and/or
#   other materials provided with the distribution.
#
#   3. Neither the name of Nordic Semiconductor ASA nor the names of other
#   contributors to this software may be used to endorse or promote products
#   derived from this software without specific prior written permission.
#
#   4. This software must only be used in or with a processor manufactured by Nordic
#   Semiconductor ASA, or in or with a processor manufactured by a third party that
#   is used in combination with a processor manufactured by Nordic Semiconductor.
#
#   5. Any software provided in binary or object form under this license must not be
#   reverse engineered, decompiled, modified and/or disassembled.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
import sys
import time
import logging
from queue import Queue, Empty
from pc_ble_driver_py.observers import *

TARGET_DEV_NAME = "HiCardi-00010"
CONNECTIONS = 1
CFG_TAG = 1


list_scan = []                      ##전역
list_mac = []
list_peer_addr = []

def init(conn_ic_id, selected_serial_port):
    # noinspection PyGlobalUndefined
    global config, BLEDriver, BLEAdvData, BLEEvtID, BLEAdapter, BLEEnableParams, BLEGapTimeoutSrc, BLEUUID, BLEUUIDBase, BLEConfigCommon, BLEConfig, BLEConfigConnGatt, BLEGapScanParams
    from pc_ble_driver_py import config

    config.__conn_ic_id__ = conn_ic_id
    # noinspection PyUnresolvedReferences
    from pc_ble_driver_py.ble_driver import (
        BLEDriver,
        BLEAdvData,
        BLEEvtID,
        BLEEnableParams,
        BLEGapTimeoutSrc,
        BLEUUID,
        BLEUUIDBase,
        BLEGapScanParams,
        BLEConfigCommon,
        BLEConfig,
        BLEConfigConnGatt,
    )

    # noinspection PyUnresolvedReferences
    from pc_ble_driver_py.ble_adapter import BLEAdapter

    global nrf_sd_ble_api_ver
    nrf_sd_ble_api_ver = config.sd_api_ver_get()

    print("Serial port used: {}".format(selected_serial_port))
    driver = BLEDriver(
        serial_port=selected_serial_port, auto_flash=False, baud_rate=1000000, log_severity_level="info"
    )
    adapter = BLEAdapter(driver)
    collector = HCICollector(adapter)

    return collector


class HCICollector(BLEDriverObserver, BLEAdapterObserver):
    def __init__(self, adapter):
        super(HCICollector, self).__init__()
        self.first = 1
        self.adapter = adapter
        self.conn_q = Queue()
        self.adapter.observer_register(self)
        self.adapter.driver.observer_register(self)
        self.adapter.default_mtu = 1000
        self.hci_base = BLEUUIDBase([
            0x6e, 0x40, 0x00, 0x00, 0xb5, 0xa3, 0xf3, 0x93, 0xe0, 0xa9, 0xe5, 0x0e, 0x24, 0xdc, 0xca, 0x9e
        ])
        self.hci_rx = BLEUUID(0x0002, self.hci_base)
        self.hci_tx = BLEUUID(0x0003, self.hci_base)

    def open(self):
        self.adapter.driver.open()
        gatt_cfg = BLEConfigConnGatt()
        gatt_cfg.att_mtu = self.adapter.default_mtu
        gatt_cfg.tag = CFG_TAG
        self.adapter.driver.ble_cfg_set(BLEConfig.conn_gatt, gatt_cfg)

        self.adapter.driver.ble_enable()
        self.adapter.driver.ble_vs_uuid_add(self.hci_base)

    def close(self):
        self.adapter.driver.close()

##################################################################################
    def scan(self):
        scan_duration = 5
        params = BLEGapScanParams(interval_ms=200, window_ms=150, timeout_s=scan_duration)
        self.adapter.driver.ble_gap_scan_start(scan_params=params)              #on_gap_evt_adv_report로 가서 리스트생성

    def write(self, dev_name, dev_num):#########dada
        scan_duration = 5
        # dev_name = target
        # dev_num = number
        # new_conn = self.conn_q.get(timeout=scan_duration)
        count = list_scan.index(dev_name)       #이름리스트 찾기
        time.sleep(3)
        peer_addr = list_peer_addr[count]
        self.adapter.connect(peer_addr, tag=CFG_TAG)    #연결

        try:
            new_conn = self.conn_q.get(timeout=scan_duration)
            self.adapter.service_discovery(new_conn)

        except Empty:
            print("No device advertising with name {TARGET_DEV_NAME} found.")
            return None

        data = ([0x80, 0x82, 0x00, 0x00, 0x8F])
        dev_num = int(dev_num)

        if dev_num > 127:
            n2 = dev_num // 128
            n3 = dev_num % 128
            data[2] =n2
            data[3] = n3
        else:
            n3 = dev_num %128
            data[3] = n3
        self.adapter.write_cmd(new_conn, self.hci_rx, data)         #write 이름

#####################################################################################

    # def connect_and_discover(self):
    #     scan_duration = 5
    #     params = BLEGapScanParams(interval_ms=200, window_ms=150, timeout_s=scan_duration)
    #     message = "We are connected!\r\n"
    #
    #     self.adapter.driver.ble_gap_scan_start(scan_params=params)
    #
    #     try:
    #         new_conn = self.conn_q.get(timeout=scan_duration)
    #         self.adapter.service_discovery(new_conn)
    #         self.adapter.enable_notification(new_conn, self.hci_tx)
    #         data = [ord(n) for n in list(message)]
    #         self.adapter.write_cmd(new_conn, self.hci_rx, data)
    #         return new_conn
    #     except Empty:
    #         print("No device advertising with name {TARGET_DEV_NAME} found.")
    #         return None
    # def on_gattc_evt_exchange_mtu_rsp(self, ble_driver, conn_handle, status, att_mtu):
    #     print("ATT MTU updated to {}".format(att_mtu))
    #
    # def on_gap_evt_data_length_update(
    #         self, ble_driver, conn_handle, data_length_params
    # ):
    #     print("Max rx octets: {}".format(data_length_params.max_rx_octets))
    #     print("Max tx octets: {}".format(data_length_params.max_tx_octets))
    #     print("Max rx time: {}".format(data_length_params.max_rx_time_us))
    #     print("Max tx time: {}".format(data_length_params.max_tx_time_us))
    #
    # def on_gatts_evt_exchange_mtu_request(self, ble_driver, conn_handle, client_mtu):
    #     print("Client requesting to update ATT MTU to {} bytes".format(client_mtu))

    def on_gap_evt_connected(
            self, ble_driver, conn_handle, peer_addr, role, conn_params
    ):
        print("New connection: {}".format(conn_handle))
        self.conn_q.put(conn_handle)

    def on_gap_evt_disconnected(self, ble_driver, conn_handle, reason):
        print("Disconnected: {} {}".format(conn_handle, reason))

    def on_gap_evt_adv_report(                                      #연결 결과
            self, ble_driver, conn_handle, peer_addr, rssi, adv_type, adv_data,
    ):
        if BLEAdvData.Types.complete_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.complete_local_name]
        elif BLEAdvData.Types.short_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.short_local_name]
        else:
            return

        dev_name = "".join(chr(e) for e in dev_name_list)
        address_string = "".join("{0:02X}".format(b) for b in peer_addr.addr)

        if list_scan.count(dev_name) == 0 :                             ######리스트만들기
            list_scan.append(dev_name)
            list_mac.append(address_string)
            list_peer_addr.append(peer_addr)
           # print(list_scan)
            # print(list_mac)

        #
        # print(
        #     "Received advertisment report, address: 0x{}, device_name: {}".format(
        #         address_string, dev_name
        #     )
        #  )
        #
        # if dev_name == TARGET_DEV_NAME:
        #     self.adapter.connect(peer_addr, tag=CFG_TAG)
        #

    # def on_notification(self, ble_adapter, conn_handle, uuid, data):      #notify
    #     if len(data) > 32:
    #         data = "({}...)".format(data[0:42])
    #     print("Connection: {}, {} = {}".format(conn_handle, uuid, data))


def scan(collector):

    collector.open()
    print("scan")
    scan_conn = collector.scan()
    time.sleep(5)
    collector.close()

def write(collector,target,number):
    #
    # conn = collector.connect_and_discover()
    # print("하이카디 선택")
    collector.open()
    collector.write(target ,number)
    collector.close()


#
# if __name__ == "__main__":
#
#     init("NRF52")
#     main("COM6")
#     quit()

# num = 300
#
# n1 = num//128
# n2 = hex(n1)
#
# list = [0x11, 0x22]
# print(type(list))
# print(type(list[1]))