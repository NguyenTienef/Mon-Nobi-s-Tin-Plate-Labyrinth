#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_dtc_testcase.py
=========================

Sinh tu dong block testcase XML (CANoe TestModule) cho mot DTC "Communication
error BCM message" moi, dua theo mau co san trong ReadDTC.xml (vi du:
BCM_VOLTAGE (0x10A)).

Voi MOI message/DTC moi, script se tao ra 3 testgroup (cho 3 loai sac):
    AC-Normal, AC-HLC, DC-HLC
Trong moi loai sac, tao tiep 3 testgroup loi:
    CRC, ALC, MISSING
Va trong moi loai loi, tao 2 testgroup dieu kien:
    "When Charging"  (dang sac)
    "Before Charging" (truoc khi sac)

=> Tong cong: 3 (loai sac) x 3 (loai loi) x 2 (dieu kien) = 18 testcase block.

Block moi duoc tu dong chen vao file XML, ngay sau block message hien co
cuoi cung trong moi testgroup title="DTC" (tuc la chen lam phan tu cuoi cung
truoc khi dong tag </testgroup> cua "DTC"). Voi file ReadDTC.xml goc, dieu nay
tuong duong voi "chen ngay sau testgroup BCM_VOLTAGE (0x10A)" nhu yeu cau.

CACH DUNG
---------
    python3 generate_dtc_testcase.py \\
        --input ReadDTC.xml \\
        --output ReadDTC_new.xml \\
        --msg-name BMS_CURRENT \\
        --msg-id 10B \\
        --dtc-crc C33184 --mature-crc 500 --demature-crc 1000 \\
        --dtc-alc C23183 --mature-alc 200 --demature-alc 400 \\
        --channel BCAN_E2E

Neu khong truyen --dtc-alc / --mature-alc / --demature-alc, script se dung
lai cung gia tri voi CRC/MISSING (--dtc-crc/--mature-crc/--demature-crc).
Trong file mau, ALC dung mot ma DTC + thoi gian rieng (C23182, 200/400) khac
voi CRC/MISSING (C33183, 500/1000) - neu du an cua ban cung quy uoc nhu vay,
hay truyen --dtc-alc rieng.

GHI CHU VE Type_Check
----------------------
Doc lai toan bo 3 block sac (AC-Normal / AC-HLC / DC-HLC) co san trong file,
gia tri Type_Check thuc te (sysvar, khong phai text title - vi text title
trong file goc co vai noi bi ghi sai/copy-paste nham) la:
    - CRC      : Type_Check = 1  (ca "When Charging" va "Before Charging")
    - ALC      : Type_Check = 1 ("When Charging"), 2 ("Before Charging")
    - MISSING  : Type_Check = 2  (ca hai dieu kien)
Script dung dung cac gia tri nay lam mac dinh (co the doi trong CONFIG o
duoi neu can).
"""

import argparse
import re
import sys
import os

DEFAULT_INPUT_XML = r"./output/ReadDTC_Official.xml"
DEFAULT_OUTPUT_XML = r"./output/ReadDTC_Official.xml"

# --------------------------------------------------------------------------- #
# 1. CAC MAU (TEMPLATE) XML DUNG CHUNG
# --------------------------------------------------------------------------- #

def ind(level):
    """2 spaces / level, giong style cua file goc."""
    return "  " * level


def set_dtc_block(level, dtc, mature, demature, msg_id, channel, type_check):
    msg_id_disp = "0x" + msg_id
    title = (f"Set DTC={dtc}, DTC_time_mature={mature}, "
             f"DTC_time_demature={demature}, Msg_ID={msg_id_disp}, "
             f"Type_Check={type_check}")
    i = ind(level)
    return (
        f'{i}<testcase ident="" title="{title}">\n'
        f'{i}  <initialize title="{title}">\n'
        f'{i}    <sysvar name="DTC" namespace="Control">{dtc}</sysvar>\n'
        f'{i}    <sysvar name="DTC_time_mature" namespace="Control">{mature}</sysvar>\n'
        f'{i}    <sysvar name="DTC_time_demature" namespace="Control">{demature}</sysvar>\n'
        f'{i}    <sysvar name="Msg_ID" namespace="{channel}">{msg_id}</sysvar>\n'
        f'{i}    <!-- <sysvar name="Msg_ID" namespace="Control::E2E">{msg_id_disp}</sysvar> -->\n'
        f'{i}    <sysvar name="Type_Check" namespace="Control">{type_check}</sysvar>\n'
        f'{i}    </initialize>\n'
        f'{i}  </testcase>\n'
    )


def templateinstance_block(level, name):
    i = ind(level)
    return (
        f'{i}<templateinstances template="{name}">\n'
        f'{i}  <testcaseinstance ident="{name}" title="{name}">\n'
        f'{i}    </testcaseinstance>\n'
        f'{i}  </templateinstances>\n'
    )


def precondition_normal_block(level):
    i = ind(level)
    return (
        f'{i}<templateinstances template="Precondition_Normal">\n'
        f'{i}  <testcaseinstance ident="Precondition_Normal" title="Precondition_Normal">\n'
        f'{i}    <paramvalue name="voltage">12</paramvalue>\n'
        f'{i}    </testcaseinstance>\n'
        f'{i}  </templateinstances>\n'
        + templateinstance_block(level, "EVCC_In_Not_Charging")
    )


def set_sysvar_block(level, sysvar_name, value, channel):
    i = ind(level)
    title = f"Set {sysvar_name}={value}"
    return (
        f'{i}<testcase ident="" title="{title}">\n'
        f'{i}  <initialize title="{title}">\n'
        f'{i}    <sysvar name="{sysvar_name}" namespace="{channel}">{value}</sysvar>\n'
        f'{i}    </initialize>\n'
        f'{i}  </testcase>\n'
    )


def wait_block(level, duration):
    i = ind(level)
    title = f"Wait for {duration}"
    return (
        f'{i}<testcase ident="" title="{title}">\n'
        f'{i}  <untilend wait="{duration}" title="{title}">\n'
        f'{i}    </untilend>\n'
        f'{i}  </testcase>\n'
    )


def fault_triggered_check_block(level):
    """Check ngay sau khi loi duoc kich hoat (dung cho 'When Charging')."""
    i = ind(level)
    title = "EVCC_VehChgCompError_Sts eq 0x02 [Error Level 2], EVCC_evt_bE2eBcmMsg eq 1"
    return (
        f'{i}<testcase ident="" title="{title}">\n'
        f'{i}  <awaitvaluematch timeout="1s" joincondition="and" title="{title}">\n'
        f'{i}    <cansignal name="IVC_EVCC_VehChgCompError_Sts" msg="IVC_EVCC_Charging_Sts" bus="ICAN"><eq>2</eq></cansignal>\n'
        # f'{i}    <cansignal name="IVC_EVCC_evt_bE2eBcmMsg" msg="IVC_EVCC_EventMatrix" bus="PCAN"><eq>1</eq></cansignal>\n'
        f'{i}    </awaitvaluematch>\n'
        f'{i}  </testcase>\n'
    )


def no_error_nochange_block(level):
    """Check loi het / khong doi trong 3s, dung sau khi xoa co loi ('When Charging')."""
    i = ind(level)
    title = ("EVCC_VehChgCompError_Sts eq 0x00 [No error], EVCC_evt_bE2eBcmMsg eq 0 ; "
              "EVCC_VehChgCompError_Sts nochange during 3s ; Wait for 3s")
    sub_title = "EVCC_VehChgCompError_Sts eq 0x00 [No error], EVCC_evt_bE2eBcmMsg eq 0"
    return (
        f'{i}<testcase ident="" title="{title}">\n'
        f'{i}  <awaitvaluematch timeout="1s" joincondition="and" title="{sub_title}">\n'
        f'{i}    <cansignal name="IVC_EVCC_VehChgCompError_Sts" msg="IVC_EVCC_Charging_Sts" bus="ICAN"><eq>0x00</eq></cansignal>\n'
        #f'{i}    <cansignal name="IVC_EVCC_evt_bE2eBcmMsg" msg="IVC_EVCC_EventMatrix" bus="PCAN"><eq>0</eq></cansignal>\n'
        f'{i}    </awaitvaluematch>\n'
        f'{i}  <conditions title="EVCC_VehChgCompError_Sts nochange during 3s">\n'
        f'{i}    <novaluechange title="EVCC_VehChgCompError_Sts nochange">\n'
        f'{i}      <cansignal name="IVC_EVCC_VehChgCompError_Sts" msg="IVC_EVCC_Charging_Sts" bus="ICAN"></cansignal>\n'
        f'{i}      </novaluechange>\n'
        f'{i}    </conditions>\n'
        f'{i}  <untilend wait="3s" title="Wait for 3s">\n'
        f'{i}    </untilend>\n'
        f'{i}  </testcase>\n'
    )


def no_error_before_block(level, evt_value):
    """Check chua co loi truoc khi cam sung ('Before Charging')."""
    i = ind(level)
    title = (f"EVCC_VehChgCompError_Sts eq 0x00 [No error], "
              f"EVCC_evt_bE2eBcmMsg eq {evt_value} ; Wait for 2s")
    sub_title = (f"EVCC_VehChgCompError_Sts eq 0x00 [No error], "
                 f"EVCC_evt_bE2eBcmMsg eq {evt_value}")
    return (
        f'{i}<testcase ident="" title="{title}">\n'
        f'{i}  <awaitvaluematch timeout="1s" joincondition="and" title="{sub_title}">\n'
        f'{i}    <cansignal name="IVC_EVCC_VehChgCompError_Sts" msg="IVC_EVCC_Charging_Sts" bus="ICAN"><eq>0</eq></cansignal>\n'
        #f'{i}    <cansignal name="IVC_EVCC_evt_bE2eBcmMsg" msg="IVC_EVCC_EventMatrix" bus="PCAN"><eq>{evt_value}</eq></cansignal>\n'
        f'{i}    </awaitvaluematch>\n'
        f'{i}  <untilend wait="2s" title="Wait for 2s">\n'
        f'{i}    </untilend>\n'
        f'{i}  </testcase>\n'
    )


def error_level2_before_block(level):
    """Check loi Level 2 sau khi cam sung trong khi DTC da bi set ('Before Charging')."""
    i = ind(level)
    title = "EVCC_VehChgCompError_Sts eq 0x02 [Error Level 2], EVCC_evt_bE2eBcmMsg eq 1 ; Wait for 2s"
    sub_title = "EVCC_VehChgCompError_Sts eq 0x02 [Error Level 2], EVCC_evt_bE2eBcmMsg eq 1"
    return (
        f'{i}<testcase ident="" title="{title}">\n'
        f'{i}  <awaitvaluematch timeout="1s" joincondition="and" title="{sub_title}">\n'
        f'{i}    <cansignal name="IVC_EVCC_VehChgCompError_Sts" msg="IVC_EVCC_Charging_Sts" bus="ICAN"><eq>2</eq></cansignal>\n'
        #f'{i}    <cansignal name="IVC_EVCC_evt_bE2eBcmMsg" msg="IVC_EVCC_EventMatrix" bus="PCAN"><eq>1</eq></cansignal>\n'
        f'{i}    </awaitvaluematch>\n'
        f'{i}  <untilend wait="2s" title="Wait for 2s">\n'
        f'{i}    </untilend>\n'
        f'{i}  </testcase>\n'
    )


# --------------------------------------------------------------------------- #
# 2. CAU HINH RIENG CHO TUNG LOAI SAC (AC-Normal / AC-HLC / DC-HLC)
# --------------------------------------------------------------------------- #

CHARGE_TYPES = {
    "AC-Normal": {
        # Cac templateinstance noi tiep nhau de dua EVCC tu "Plug-in" den
        # "dang sac" (dung trong testgroup "When Charging").
        "ramp_to_charging": [
            "GunPlugin",
            "EVCC_In_Plug_In",
            "EVCC_In_AC_Basic_Charging_In_Progress_On_Normal",
        ],
        # Template dung khi loi xay ra ngay sau khi cam sung (testgroup
        # "Before Charging"), va cung la template dung de "release" loi
        # trong testgroup "When Charging".
        "fault_gun_release": "EVCC_In_AC_Basic_Charging_Fault_Gun_Release",
    },
    "AC-HLC": {
        "ramp_to_charging": [
            "GunPlugin",
            "EVCC_In_Plug_In",
            "EVCC_In_Gun_Locked_PWM_5",
            "EVCC_In_AC_HLC_Authenticating",
            "EVCC_In_AC_HLC_ChargeParameterDiscovery",
            "EVCC_In_AC_HLC_PowerDeliveryStart",
            "EVCC_In_AC_HLC_Charging_In_Process_On_Normal",
        ],
        "fault_gun_release": "EVCC_In_AC_HLC_Charging_Fault_Gun_Release",
    },
    "DC-HLC": {
        "ramp_to_charging": [
            "GunPlugin",
            "EVCC_In_Plug_In",
            "EVCC_In_Gun_Locked_PWM_5",
            "EVCC_In_DC_HLC_ChargeParameterDiscovery",
            "EVCC_In_DC_HLC_CableCheck_B2C",
            "EVCC_In_DC_HLC_PreCharge",
            "EVCC_In_DC_HLC_Charging_In_Process",
        ],
        "fault_gun_release": "EVCC_In_DC_HLC_Charging_Fault_Gun_Release",
    },
}

# Thu tu duyet (giu dung thu tu nhu file goc)
CHARGE_TYPE_ORDER = ["AC-Normal", "AC-HLC", "DC-HLC"]


# --------------------------------------------------------------------------- #
# 3. CAU HINH RIENG CHO TUNG LOAI LOI (CRC / ALC / MISSING)
# --------------------------------------------------------------------------- #

def build_fault_types(args):
    """Tra ve dict cau hinh CRC / ALC / MISSING dua tren tham so dau vao."""
    dtc_alc = args.dtc_alc or args.dtc_crc
    mature_alc = args.mature_alc if args.mature_alc is not None else args.mature_crc
    demature_alc = args.demature_alc if args.demature_alc is not None else args.demature_crc

    dtc_missing = args.dtc_missing or args.dtc_crc
    mature_missing = args.mature_missing if args.mature_missing is not None else args.mature_crc
    demature_missing = args.demature_missing if args.demature_missing is not None else args.demature_crc

    return {
        "CRC": {
            "sysvar_name": "wrong_crc",
            "dtc": args.dtc_crc,
            "mature": args.mature_crc,
            "demature": args.demature_crc,
            "type_check_when": 1,
            "type_check_before": 1,
            "evt_value_before": 0,
            "reset_to_zero": True,
        },
        "ALC": {
            "sysvar_name": "wrong_alc",
            "dtc": dtc_alc,
            "mature": mature_alc,
            "demature": demature_alc,
            "type_check_when": 1,
            "type_check_before": 2,
            "evt_value_before": 1,
            "reset_to_zero": True,
        },
        "MISSING": {
            "sysvar_name": "Timeout_e2e",
            "dtc": dtc_missing,
            "mature": mature_missing,
            "demature": demature_missing,
            "type_check_when": 2,
            "type_check_before": 2,
            "evt_value_before": 1,
            "reset_to_zero": True,
        },
    }


FAULT_TYPE_ORDER = ["CRC", "ALC", "MISSING"]


# --------------------------------------------------------------------------- #
# 4. SINH 1 TESTGROUP "When Charging" / "Before Charging"
# --------------------------------------------------------------------------- #

def build_when_charging(level, charge_cfg, fault_cfg, msg_id, channel):
    i = ind(level)
    out = [f'{i}<testgroup title="When Charging">\n']
    out.append(set_dtc_block(level + 1, fault_cfg["dtc"], fault_cfg["mature"],
                              fault_cfg["demature"], msg_id, channel,
                              fault_cfg["type_check_when"]))
    out.append(precondition_normal_block(level + 1))
    for tmpl in charge_cfg["ramp_to_charging"]:
        out.append(templateinstance_block(level + 1, tmpl))
    out.append(set_sysvar_block(level + 1, fault_cfg["sysvar_name"], 1, channel))
    out.append(templateinstance_block(level + 1, "DTC_1906_Timing_Dual_For_NW"))
    out.append(fault_triggered_check_block(level + 1))
    out.append(wait_block(level + 1, "3s"))
    out.append(templateinstance_block(level + 1, charge_cfg["fault_gun_release"]))
    reset_value = 0 if fault_cfg["reset_to_zero"] else 1
    out.append(set_sysvar_block(level + 1, fault_cfg["sysvar_name"], reset_value, channel))
    out.append(templateinstance_block(level + 1, "DTC_1906_Timing_Dual_For_NW"))
    out.append(no_error_nochange_block(level + 1))
    out.append(wait_block(level + 1, "3s"))
    out.append(templateinstance_block(level + 1, "GunUnPlugin"))
    out.append(templateinstance_block(level + 1, "EVCC_In_Not_Charging"))
    out.append(templateinstance_block(level + 1, "Postcondition_Normal-PowerON"))
    out.append(f'{i}</testgroup>\n')
    return "".join(out)


def build_before_charging(level, charge_cfg, fault_cfg, msg_id, channel):
    i = ind(level)
    out = [f'{i}<testgroup title="Before Charging">\n']
    out.append(set_dtc_block(level + 1, fault_cfg["dtc"], fault_cfg["mature"],
                              fault_cfg["demature"], msg_id, channel,
                              fault_cfg["type_check_before"]))
    out.append(precondition_normal_block(level + 1))
    out.append(set_sysvar_block(level + 1, fault_cfg["sysvar_name"], 1, channel))
    out.append(templateinstance_block(level + 1, "DTC_1906_Timing_Dual_For_NW"))
    out.append(no_error_before_block(level + 1, fault_cfg["evt_value_before"]))
    out.append(templateinstance_block(level + 1, "GunPlugin"))
    out.append(templateinstance_block(level + 1, charge_cfg["fault_gun_release"]))
    out.append(error_level2_before_block(level + 1))
    out.append(wait_block(level + 1, "3s"))
    reset_value = 0 if fault_cfg["reset_to_zero"] else 1
    out.append(set_sysvar_block(level + 1, fault_cfg["sysvar_name"], reset_value, channel))
    out.append(templateinstance_block(level + 1, "DTC_1906_Timing_Dual_For_NW"))
    out.append(wait_block(level + 1, "3s"))
    out.append(templateinstance_block(level + 1, "GunUnPlugin"))
    out.append(templateinstance_block(level + 1, "EVCC_In_Not_Charging"))
    out.append(templateinstance_block(level + 1, "Postcondition_Normal-PowerON"))
    out.append(f'{i}</testgroup>\n')
    return "".join(out)


def build_fault_group(level, fault_name, charge_cfg, fault_cfg, msg_id, channel):
    i = ind(level)
    out = [f'{i}<testgroup title="{fault_name}">\n']
    out.append(build_when_charging(level + 1, charge_cfg, fault_cfg, msg_id, channel))
    out.append(build_before_charging(level + 1, charge_cfg, fault_cfg, msg_id, channel))
    out.append(f'{i}</testgroup>\n')
    return "".join(out)


def build_message_group(level, msg_name, msg_id, channel, charge_type, fault_types):
    """Sinh: <testgroup title="Communication error message: NAME (0xID)"> ... """
    i = ind(level)
    charge_cfg = CHARGE_TYPES[charge_type]
    title = f"Communication error message: {msg_name} (0x{msg_id})"
    out = [f'{i}<testgroup title="{title}">\n']
    for fault_name in FAULT_TYPE_ORDER:
        out.append(build_fault_group(level + 1, fault_name, charge_cfg,
                                      fault_types[fault_name], msg_id, channel))
    out.append(f'{i}</testgroup>\n')
    return "".join(out)


# --------------------------------------------------------------------------- #
# 5. CHEN VAO FILE XML (NGAY SAU BLOCK MESSAGE CUOI CUNG TRONG MOI "DTC")
# --------------------------------------------------------------------------- #

def find_dtc_group_spans(lines):
    """
    Quet toan bo file, tra ve list cac tuple (charge_type, open_line_index,
    close_line_index). open/close_line_index la dong (0-based) chua tag mo/dong
    cua testgroup title="DTC" tuong ung. charge_type duoc xac dinh bang
    testgroup cha gan nhat (AC-Normal / AC-HLC / DC-HLC) dang mo tai thoi diem do.
    """
    stack = []  # list of (title, line_index) dang mo, theo thu tu mo
    spans = []
    open_re = re.compile(r'<testgroup\s+title="([^"]*)"\s*>')
    close_re = re.compile(r'</testgroup>')

    for idx, line in enumerate(lines):
        # Mot dong co the chua ca mo va dong (khong xay ra trong file nay,
        # nhung de an toan ta xu ly mo truoc, dong sau theo thu tu xuat hien)
        for m in open_re.finditer(line):
            stack.append((m.group(1), idx))
        n_close = len(close_re.findall(line))
        for _ in range(n_close):
            if not stack:
                continue
            title, open_idx = stack.pop()
            if title == "DTC":
                # tim charge type: phan tu con lai tren dinh stack
                charge_type = stack[-1][0] if stack else None
                spans.append((charge_type, open_idx, idx))
    return spans


def insert_new_message_blocks(xml_text, msg_name, msg_id, channel, fault_types):
    lines = xml_text.split("\n")
    spans = find_dtc_group_spans(lines)

    if not spans:
        raise RuntimeError('Khong tim thay testgroup title="DTC" nao trong file.')

    found_types = {ct for ct, _, _ in spans}
    missing = [ct for ct in CHARGE_TYPE_ORDER if ct not in found_types]
    if missing:
        print(f"[CANH BAO] Khong tim thay testgroup DTC cho loai sac: {missing}",
              file=sys.stderr)

    # Chen tu duoi len tren de khong lam lech chi so dong cua cac span khac
    spans_sorted = sorted(spans, key=lambda x: x[2], reverse=True)

    for charge_type, open_idx, close_idx in spans_sorted:
        if charge_type not in CHARGE_TYPES:
            continue
        # Suy ra level dua theo dong MO cua testgroup DTC (on dinh hon dong
        # dong, vi cac dong dong trong file goc bi tron lan tab/space).
        open_line = lines[open_idx]
        open_indent_str = re.match(r'[ \t]*', open_line).group(0)
        open_indent_str = open_indent_str.replace("\t", "  ")
        level = (len(open_indent_str) // 2) + 1

        block = build_message_group(level, msg_name, msg_id, channel,
                                     charge_type, fault_types)
        block_lines = block.rstrip("\n").split("\n")
        # Chen ngay TRUOC dong </testgroup> cua "DTC" (tuc la lam phan tu
        # cuoi cung trong testgroup DTC - ngay sau block message cuoi cung
        # hien co, ví dụ BCM_VOLTAGE).
        lines[close_idx:close_idx] = block_lines

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 6. MAIN / CLI
# --------------------------------------------------------------------------- #

def parse_args():
    p = argparse.ArgumentParser(
        description="Generate DTC testcase XML")

    p.add_argument("--input")
    p.add_argument("--output")
    p.add_argument("--msg-name")
    p.add_argument("--msg-id")
    p.add_argument("--channel", default="BCAN_E2E")

    p.add_argument("--dtc-crc")
    p.add_argument("--mature-crc", type=int)
    p.add_argument("--demature-crc", type=int)

    p.add_argument("--dtc-alc", default=None)
    p.add_argument("--mature-alc", type=int, default=None)
    p.add_argument("--demature-alc", type=int, default=None)

    p.add_argument("--dtc-missing", default=None)
    p.add_argument("--mature-missing", type=int, default=None)
    p.add_argument("--demature-missing", type=int, default=None)

    args = p.parse_args()

    if len(sys.argv) == 1:
        print("========== DTC XML GENERATOR ==========")

        args.input = DEFAULT_INPUT_XML
        args.output = DEFAULT_OUTPUT_XML
        print(f"Input XML  : {args.input}")
        print(f"Output XML : {args.output}")

        args.msg_name = input("Message Name: ").strip()
        args.msg_id = input("Message ID (hex, vd 10B): ").strip().upper()

        args.channel = (
            input(f"Channel [{args.channel}]: ").strip()
            or args.channel
        )

        args.dtc_crc = input(
            "CRC DTC: "
        ).strip().upper()

        args.mature_crc = int(input("CRC Mature Time (ms): ").strip())
        args.demature_crc = int(input("CRC Demature Time (ms): ").strip())

        alc = input(
            "ALC DTC (Enter = same CRC): "
        ).strip().upper()
        args.dtc_alc = alc if alc else None

        alc_mature = input(
            "ALC Mature Time (Enter = same CRC): "
        ).strip()
        args.mature_alc = int(alc_mature) if alc_mature else None

        alc_demature = input(
            "ALC Demature Time (Enter = same CRC): "
        ).strip()
        args.demature_alc = int(alc_demature) if alc_demature else None

        miss = input("MISSING DTC (Enter = same CRC): ").strip().upper()
        args.dtc_missing = miss if miss else None

        miss_mature = input("MISSING Mature Time (Enter = same CRC): ").strip()
        args.mature_missing = int(miss_mature) if miss_mature else None

        miss_demature = input("MISSING Demature Time (Enter = same CRC): ").strip()
        args.demature_missing = int(miss_demature) if miss_demature else None

    required = [
        "input", "output", "msg_name", "msg_id",
        "dtc_crc", "mature_crc", "demature_crc"
    ]

    missing = [x for x in required if getattr(args, x) is None]
    if missing:
        p.error("Missing required arguments: " + ", ".join(missing))

    return args


def main():
    args = parse_args()

    if not os.path.exists(args.input):
        print(f"\n[ERROR] Input file not found: {args.input}")
        return

    output_dir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(output_dir, exist_ok=True)

    with open(args.input, "r", encoding="ISO-8859-1") as f:
        xml_text = f.read()

    fault_types = build_fault_types(args)

    new_xml = insert_new_message_blocks(
        xml_text, args.msg_name, args.msg_id, args.channel, fault_types)

    with open(args.output, "w", encoding="ISO-8859-1", newline="\n") as f:
        f.write(new_xml)

    print(f"Da sinh xong: {args.output}")
    print(f"  Message     : {args.msg_name} (0x{args.msg_id})")
    print(f"  Channel     : {args.channel}")
    print(f"  CRC  : {args.dtc_crc} "
          f"(mature={args.mature_crc}, demature={args.demature_crc})")
    print(f"  ALC DTC            : {fault_types['ALC']['dtc']} "
          f"(mature={fault_types['ALC']['mature']}, "
          f"demature={fault_types['ALC']['demature']})")
    print(f"  MISSING DTC        : {fault_types['MISSING']['dtc']} "
          f"(mature={fault_types['MISSING']['mature']}, "
          f"demature={fault_types['MISSING']['demature']})")
    print("  Da them 3 testgroup (AC-Normal / AC-HLC / DC-HLC), "
          "moi testgroup gom CRC/ALC/MISSING x When/Before Charging.")


if __name__ == "__main__":
    main()