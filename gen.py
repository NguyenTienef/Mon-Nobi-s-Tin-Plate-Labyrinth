#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DTC XML Generator - Charge Inhibit Version
Chèn testcases DTC vào file XML hiện có bằng terminal input.
Hỗ trợ: 3 loại sạc (AC-Normal, AC-HLC, DC-HLC) x 3 loại lỗi (CRC, ALC, MISSING) x 2 trường hợp (When Charging, Before Charging)
"""

import os
import sys
import re

# ─── HELPERS ────────────────────────────────────────────────────────────────

def ind(level):
    """2 spaces / level, giống style của file gốc."""
    return "  " * level


def set_dtc_block(level, dtc, mature, demature, msg_id, channel, type_check):
    """Tạo khối set DTC parameters."""
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
        f'{i}    <sysvar name="Type_Check" namespace="Control">{type_check}</sysvar>\n'
        f'{i}    </initialize>\n'
        f'{i}  </testcase>\n'
    )


def templateinstance_block(level, name):
    """Tạo khối template instance."""
    i = ind(level)
    return (
        f'{i}<templateinstances template="{name}">\n'
        f'{i}  <testcaseinstance ident="{name}" title="{name}">\n'
        f'{i}    </testcaseinstance>\n'
        f'{i}  </templateinstances>\n'
    )


def precondition_normal_block(level):
    """Tạo khối precondition."""
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
    """Tạo khối set sysvar."""
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
    """Tạo khối chờ."""
    i = ind(level)
    title = f"Wait for {duration}"
    return (
        f'{i}<testcase ident="" title="{title}">\n'
        f'{i}  <untilend wait="{duration}" title="{title}">\n'
        f'{i}    </untilend>\n'
        f'{i}  </testcase>\n'
    )


def fault_triggered_check_block(level):
    """Check lỗi được kích hoạt (dùng cho 'When Charging')."""
    i = ind(level)
    title = "EVCC_VehChgCompError_Sts eq 0x02 [Error Level 2], EVCC_evt_bE2eBcmMsg eq 1"
    return (
        f'{i}<testcase ident="" title="{title}">\n'
        f'{i}  <awaitvaluematch timeout="1s" joincondition="and" title="{title}">\n'
        f'{i}    <cansignal name="IVC_EVCC_VehChgCompError_Sts" msg="IVC_EVCC_Charging_Sts" bus="ICAN"><eq>2</eq></cansignal>\n'
        f'{i}    </awaitvaluematch>\n'
        f'{i}  </testcase>\n'
    )


def no_error_nochange_block(level):
    """Check lỗi hết / không đổi trong 3s, dùng sau khi xoá lỗi ('When Charging')."""
    i = ind(level)
    title = ("EVCC_VehChgCompError_Sts eq 0x00 [No error], EVCC_evt_bE2eBcmMsg eq 0 ; "
              "EVCC_VehChgCompError_Sts nochange during 3s ; Wait for 3s")
    sub_title = "EVCC_VehChgCompError_Sts eq 0x00 [No error], EVCC_evt_bE2eBcmMsg eq 0"
    return (
        f'{i}<testcase ident="" title="{title}">\n'
        f'{i}  <awaitvaluematch timeout="1s" joincondition="and" title="{sub_title}">\n'
        f'{i}    <cansignal name="IVC_EVCC_VehChgCompError_Sts" msg="IVC_EVCC_Charging_Sts" bus="ICAN"><eq>0x00</eq></cansignal>\n'
        f'{i}    <cansignal name="IVC_EVCC_evt_bE2eBcmMsg" msg="IVC_EVCC_EventMatrix" bus="PCAN"><eq>0</eq></cansignal>\n'
        f'{i}    </awaitvaluematch>\n'
        f'{i}  <conditions title="EVCC_VehChgCompError_Sts nochange during 3s">\n'
        f'{i}    <novaluechange title="EVCC_VehChgCompError_Sts nochange">\n'
        f'{i}      <cansignal name="IVC_EVCC_VehChgCompError_Sts" msg="IVC_EVCC_Charging_Sts" bus="ICAN"></cansignal>\n'
        f'{i}      </novaluechange>\n'
        f'{i}    </conditions>\n'
        f'{i}  <untilend wait="3s" title="Wait for 3s">\n'
        f'{i}    </untilend>\n'
        f'{i}  </testcase>\n'
        f'{i}<testcase ident="" title="Wait for 3s">\n'
        f'{i}  <untilend wait="3s" title="Wait for 3s">\n'
        f'{i}    </untilend>\n'
        f'{i}  </testcase>\n'
    )


def no_error_before_block(level, evt_value):
    """Check chưa có lỗi trước khi cắm súng ('Before Charging')."""
    i = ind(level)
    title = (f"EVCC_VehChgCompError_Sts eq 0x00 [No error], "
              f"EVCC_evt_bE2eBcmMsg eq {evt_value} ; Wait for 2s")
    sub_title = (f"EVCC_VehChgCompError_Sts eq 0x00 [No error], "
                 f"EVCC_evt_bE2eBcmMsg eq {evt_value} ; Wait for 2s")
    return (
        f'{i}<testcase ident="" title="{title}">\n'
        f'{i}  <awaitvaluematch timeout="1s" joincondition="and" title="{sub_title}">\n'
        f'{i}    <cansignal name="IVC_EVCC_VehChgCompError_Sts" msg="IVC_EVCC_Charging_Sts" bus="ICAN"><eq>0</eq></cansignal>\n'
        f'{i}    <cansignal name="IVC_EVCC_evt_bE2eBcmMsg" msg="IVC_EVCC_EventMatrix" bus="PCAN"><eq>{evt_value}</eq></cansignal>\n'
        f'{i}    </awaitvaluematch>\n'
        f'{i}  <untilend wait="2s" title="Wait for 2s">\n'
        f'{i}    </untilend>\n'
        f'{i}  </testcase>\n'
    )


def error_level2_before_block(level):
    """Check lỗi Level 2 sau khi cắm súng trong khi DTC đã bị set ('Before Charging')."""
    i = ind(level)
    title = "EVCC_VehChgCompError_Sts eq 0x02 [Error Level 2], EVCC_evt_bE2eBcmMsg eq 1 ; Wait for 2s"
    sub_title = "EVCC_VehChgCompError_Sts eq 0x02 [Error Level 2], EVCC_evt_bE2eBcmMsg eq 1"
    return (
        f'{i}<testcase ident="" title="{title}">\n'
        f'{i}  <awaitvaluematch timeout="1s" joincondition="and" title="{sub_title}">\n'
        f'{i}    <cansignal name="IVC_EVCC_VehChgCompError_Sts" msg="IVC_EVCC_Charging_Sts" bus="ICAN"><eq>2</eq></cansignal>\n'
        f'{i}    </awaitvaluematch>\n'
        f'{i}  <untilend wait="2s" title="Wait for 2s">\n'
        f'{i}    </untilend>\n'
        f'{i}  </testcase>\n'
    )


# ─── CONFIGURATION ────────────────────────────────────────────────────────

CHARGE_TYPES = {
    "AC-Normal": {
        "ramp_to_charging": [
            "GunPlugin",
            "EVCC_In_Plug_In",
            "EVCC_In_AC_Basic_Charging_In_Progress_On_Normal",
        ],
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

CHARGE_TYPE_ORDER = ["AC-Normal", "AC-HLC", "DC-HLC"]


def build_fault_types(dtc_crc, mature_crc, demature_crc,
                      dtc_alc, mature_alc, demature_alc,
                      dtc_missing, mature_missing, demature_missing):
    """Tạo configuration cho CRC / ALC / MISSING."""
    return {
        "CRC": {
            "sysvar_name": "wrong_crc",
            "dtc": dtc_crc,
            "mature": mature_crc,
            "demature": demature_crc,
            "type_check_when": 1,
            "type_check_before": 1,
            "evt_value_before": 0,
        },
        "ALC": {
            "sysvar_name": "wrong_alc",
            "dtc": dtc_alc or dtc_crc,
            "mature": mature_alc if mature_alc is not None else mature_crc,
            "demature": demature_alc if demature_alc is not None else demature_crc,
            "type_check_when": 1,
            "type_check_before": 2,
            "evt_value_before": 1,
        },
        "MISSING": {
            "sysvar_name": "Timeout_e2e",
            "dtc": dtc_missing or dtc_crc,
            "mature": mature_missing if mature_missing is not None else mature_crc,
            "demature": demature_missing if demature_missing is not None else demature_crc,
            "type_check_when": 2,
            "type_check_before": 2,
            "evt_value_before": 1,
        },
    }


FAULT_TYPE_ORDER = ["CRC", "ALC", "MISSING"]


# ─── BUILD TESTGROUPS ─────────────────────────────────────────────────────

def build_when_charging(level, charge_cfg, fault_cfg, msg_id, channel):
    """Tạo testgroup 'When Charging'."""
    i = ind(level)
    out = [f'{i}<testgroup title="When Charging">\n']
    out.append(set_dtc_block(level + 1, fault_cfg["dtc"], fault_cfg["mature"],
                              fault_cfg["demature"], msg_id, channel,
                              fault_cfg["type_check_when"]))
    out.append(precondition_normal_block(level + 1))
    out.append(templateinstance_block(level + 1, "EVCC_In_Not_Charging"))
    for tmpl in charge_cfg["ramp_to_charging"]:
        out.append(templateinstance_block(level + 1, tmpl))
    out.append(set_sysvar_block(level + 1, fault_cfg["sysvar_name"], 1, channel))
    out.append(templateinstance_block(level + 1, "DTC_1906_Timing_Dual_For_NW"))
    out.append(no_error_before_block(level + 1, 0))
    out.append(wait_block(level + 1, "3s"))
    # Repeat only the last ramp template (which is the charging in progress one)
    out.append(templateinstance_block(level + 1, charge_cfg["ramp_to_charging"][-1]))
    out.append(set_sysvar_block(level + 1, fault_cfg["sysvar_name"], 0, channel))
    out.append(templateinstance_block(level + 1, "DTC_1906_Timing_Dual_For_NW"))
    out.append(no_error_nochange_block(level + 1))
    out.append(templateinstance_block(level + 1, "StopCharge"))
    # Complete template name is derived from fault_gun_release by replacing "Fault" with "Charging_Complete"
    complete_template = charge_cfg["fault_gun_release"].replace("Fault_Gun_Release", "Charging_Complete_Gun_Release")
    out.append(templateinstance_block(level + 1, complete_template))
    out.append(templateinstance_block(level + 1, "GunUnPlugin"))
    out.append(templateinstance_block(level + 1, "EVCC_In_Not_Charging"))
    out.append(templateinstance_block(level + 1, "Postcondition_Normal-PowerON"))
    out.append(f'{i}</testgroup>\n')
    return "".join(out)


def build_before_charging(level, charge_cfg, fault_cfg, msg_id, channel):
    """Tạo testgroup 'Before Charging'."""
    i = ind(level)
    out = [f'{i}<testgroup title="Before Charging">\n']
    out.append(set_dtc_block(level + 1, fault_cfg["dtc"], fault_cfg["mature"],
                              fault_cfg["demature"], msg_id, channel,
                              fault_cfg["type_check_before"]))
    out.append(precondition_normal_block(level + 1))
    out.append(templateinstance_block(level + 1, "EVCC_In_Not_Charging"))
    out.append(set_sysvar_block(level + 1, fault_cfg["sysvar_name"], 1, channel))
    out.append(templateinstance_block(level + 1, "DTC_1906_Timing_Dual_For_NW"))
    out.append(no_error_before_block(level + 1, 0))
    out.append(templateinstance_block(level + 1, "GunPlugin"))
    # Only add the last ramp template (charging in progress)
    out.append(templateinstance_block(level + 1, charge_cfg["ramp_to_charging"][-1]))
    out.append(no_error_before_block(level + 1, 0))
    out.append(wait_block(level + 1, "3s"))
    out.append(set_sysvar_block(level + 1, fault_cfg["sysvar_name"], 0, channel))
    out.append(templateinstance_block(level + 1, "DTC_1906_Timing_Dual_For_NW"))
    out.append(wait_block(level + 1, "3s"))
    out.append(templateinstance_block(level + 1, "StopCharge"))
    # Complete template name is derived from fault_gun_release by replacing "Fault" with "Charging_Complete"
    complete_template = charge_cfg["fault_gun_release"].replace("Fault_Gun_Release", "Charging_Complete_Gun_Release")
    out.append(templateinstance_block(level + 1, complete_template))
    out.append(templateinstance_block(level + 1, "GunUnPlugin"))
    out.append(templateinstance_block(level + 1, "EVCC_In_Not_Charging"))
    out.append(templateinstance_block(level + 1, "Postcondition_Normal-PowerON"))
    out.append(f'{i}</testgroup>\n')
    return "".join(out)


def build_fault_group(level, fault_name, charge_cfg, fault_cfg, msg_id, channel):
    """Tạo testgroup lỗi (chứa When/Before Charging)."""
    i = ind(level)
    out = [f'{i}<testgroup title="{fault_name}">\n']
    out.append(build_when_charging(level + 1, charge_cfg, fault_cfg, msg_id, channel))
    out.append(build_before_charging(level + 1, charge_cfg, fault_cfg, msg_id, channel))
    out.append(f'{i}</testgroup>\n')
    return "".join(out)


def build_message_group(level, msg_name, msg_id, channel, charge_type, fault_types):
    """Tạo testgroup message (chứa CRC/ALC/MISSING)."""
    i = ind(level)
    charge_cfg = CHARGE_TYPES[charge_type]
    title = f"Communication error BCM message: {msg_name} (0x{msg_id})"
    out = [f'{i}<testgroup title="{title}">\n']
    for fault_name in FAULT_TYPE_ORDER:
        out.append(build_fault_group(level + 1, fault_name, charge_cfg,
                                      fault_types[fault_name], msg_id, channel))
    out.append(f'{i}</testgroup>\n')
    return "".join(out)


# ─── INSERT TO XML ─────────────────────────────────────────────────────────

def find_dtc_group_spans(lines):
    """Tìm các testgroup 'DTC' và charge type cha của chúng."""
    stack = []
    spans = []
    open_re = re.compile(r'<testgroup\s+title="([^"]*)"\s*>')
    close_re = re.compile(r'</testgroup>')

    for idx, line in enumerate(lines):
        for m in open_re.finditer(line):
            stack.append((m.group(1), idx))
        n_close = len(close_re.findall(line))
        for _ in range(n_close):
            if not stack:
                continue
            title, open_idx = stack.pop()
            if title == "DTC":
                charge_type = stack[-1][0] if stack else None
                spans.append((charge_type, open_idx, idx))
    return spans


def insert_new_message_blocks(xml_text, msg_name, msg_id, channel, fault_types):
    """Chèn testcase mới vào file XML."""
    lines = xml_text.split("\n")
    spans = find_dtc_group_spans(lines)

    if not spans:
        raise RuntimeError('Không tìm thấy testgroup title="DTC" nào trong file.')

    found_types = {ct for ct, _, _ in spans}
    missing = [ct for ct in CHARGE_TYPE_ORDER if ct not in found_types]
    if missing:
        print(f"[CẢNH BÁO] Không tìm thấy testgroup DTC cho loại sạc: {missing}",
              file=sys.stderr)

    # Chèn từ dưới lên trên để không làm lệch chỉ số
    spans_sorted = sorted(spans, key=lambda x: x[2], reverse=True)

    for charge_type, open_idx, close_idx in spans_sorted:
        if charge_type not in CHARGE_TYPES:
            continue
        # Tính level từ indentation
        open_line = lines[open_idx]
        open_indent_str = re.match(r'[ \t]*', open_line).group(0)
        open_indent_str = open_indent_str.replace("\t", "  ")
        level = (len(open_indent_str) // 2) + 1

        block = build_message_group(level, msg_name, msg_id, channel,
                                     charge_type, fault_types)
        block_lines = block.rstrip("\n").split("\n")
        # Chèn trước dòng </testgroup> của "DTC"
        lines[close_idx:close_idx] = block_lines

    return "\n".join(lines)


# ─── MAIN ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("     DTC XML GENERATOR - CHARGE INHIBIT")
    print("=" * 50)

    input_xml = input("\nInput XML file path: ").strip()
    output_xml = input("Output XML file path: ").strip()

    if not os.path.exists(input_xml):
        print(f"\n[ERROR] Input file không tồn tại: {input_xml}")
        sys.exit(1)

    msg_name = input("\nMessage Name (vd: BCM_VOLTAGE): ").strip()
    msg_id = input("Message ID (hex, vd: 481): ").strip().upper()
    channel = input("Channel [BCAN_E2E]: ").strip() or "BCAN_E2E"

    print("\n--- CRC Error Configuration ---")
    dtc_crc = input("CRC DTC (vd: C33283): ").strip().upper()
    mature_crc = int(input("CRC Mature Time (ms, vd: 500): ").strip())
    demature_crc = int(input("CRC Demature Time (ms, vd: 1000): ").strip())

    print("\n--- ALC Error Configuration ---")
    dtc_alc_input = input("ALC DTC (Enter = same as CRC): ").strip().upper()
    dtc_alc = dtc_alc_input if dtc_alc_input else None

    mature_alc_input = input("ALC Mature Time (Enter = same as CRC): ").strip()
    mature_alc = int(mature_alc_input) if mature_alc_input else None

    demature_alc_input = input("ALC Demature Time (Enter = same as CRC): ").strip()
    demature_alc = int(demature_alc_input) if demature_alc_input else None

    print("\n--- MISSING Error Configuration ---")
    dtc_missing_input = input("MISSING DTC (Enter = same as CRC): ").strip().upper()
    dtc_missing = dtc_missing_input if dtc_missing_input else None

    mature_missing_input = input("MISSING Mature Time (Enter = same as CRC): ").strip()
    mature_missing = int(mature_missing_input) if mature_missing_input else None

    demature_missing_input = input("MISSING Demature Time (Enter = same as CRC): ").strip()
    demature_missing = int(demature_missing_input) if demature_missing_input else None

    # Đọc file XML
    with open(input_xml, "r", encoding="ISO-8859-1") as f:
        xml_text = f.read()

    # Build fault configurations
    fault_types = build_fault_types(
        dtc_crc, mature_crc, demature_crc,
        dtc_alc, mature_alc, demature_alc,
        dtc_missing, mature_missing, demature_missing
    )

    # Chèn testcase mới
    new_xml = insert_new_message_blocks(xml_text, msg_name, msg_id, channel, fault_types)

    # Ghi file XML
    os.makedirs(os.path.dirname(os.path.abspath(output_xml)) if os.path.dirname(output_xml) else ".", exist_ok=True)
    with open(output_xml, "w", encoding="ISO-8859-1", newline="\n") as f:
        f.write(new_xml)

    print(f"\n[DONE] XML đã được tạo: {output_xml}")
    print(f"  Message       : {msg_name} (0x{msg_id})")
    print(f"  Channel       : {channel}")
    print(f"  CRC DTC       : {fault_types['CRC']['dtc']} (mature={fault_types['CRC']['mature']}, demature={fault_types['CRC']['demature']})")
    print(f"  ALC DTC       : {fault_types['ALC']['dtc']} (mature={fault_types['ALC']['mature']}, demature={fault_types['ALC']['demature']})")
    print(f"  MISSING DTC   : {fault_types['MISSING']['dtc']} (mature={fault_types['MISSING']['mature']}, demature={fault_types['MISSING']['demature']})")
    print("\n  Đã thêm testcases cho 3 loại sạc (AC-Normal / AC-HLC / DC-HLC),")
    print("  mỗi loại gồm CRC/ALC/MISSING x When/Before Charging.")


if __name__ == "__main__":
    main()