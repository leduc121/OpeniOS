#!/usr/bin/env python3
"""GDB worker script executed inside gdb-multiarch to capture primary RTBuddy exception."""

import gdb
import os
import struct
import sys
import traceback

LOG_FILE_PATH = "/tmp/openios_capture_primary.log"
_log_file = None

def init_logging():
    global _log_file
    try:
        _log_file = open(LOG_FILE_PATH, "a", buffering=1)
    except Exception as e:
        print(f"[GDB-PY-WARN] Cannot open log file: {e}", flush=True)

def log(msg):
    print(msg, flush=True)
    if _log_file:
        try:
            _log_file.write(msg + "\n")
            _log_file.flush()
            os.fsync(_log_file.fileno())
        except Exception:
            pass

def decode_esr(esr):
    ec = (esr >> 26) & 0x3f
    il = (esr >> 25) & 0x1
    iss = esr & 0x1ffffff
    
    ec_names = {
        0x00: "Unknown / Unknown reason",
        0x01: "Trapped WFI/WFE",
        0x03: "Trapped MCR/MRC (CP15)",
        0x04: "Trapped MCRR/MRRC (CP15)",
        0x05: "Trapped MCR/MRC (CP14)",
        0x06: "Trapped LDC/STC",
        0x07: "Trapped FP/SIMD access",
        0x0c: "Trapped MRRC (CP14)",
        0x0e: "Illegal Execution state",
        0x11: "SVC instruction in AArch32",
        0x15: "SVC instruction in AArch64",
        0x18: "Trapped MSR/MRS system instruction",
        0x19: "Trapped SVE access",
        0x1a: "PAC fail",
        0x20: "Instruction Abort (lower EL)",
        0x21: "Instruction Abort (same EL / EL1)",
        0x22: "PC alignment fault",
        0x24: "Data Abort (lower EL)",
        0x25: "Data Abort (same EL / EL1)",
        0x26: "SP alignment fault",
        0x28: "Trapped FP exception (AArch32)",
        0x2c: "Trapped FP exception (AArch64)",
        0x2f: "SError interrupt",
        0x30: "Breakpoint (lower EL)",
        0x31: "Breakpoint (same EL / EL1)",
        0x32: "Software Step (lower EL)",
        0x33: "Software Step (same EL / EL1)",
        0x34: "Watchpoint (lower EL)",
        0x35: "Watchpoint (same EL / EL1)",
        0x38: "BKPT instruction (AArch32)",
        0x3c: "BRK instruction (AArch64)",
    }
    
    name = ec_names.get(ec, f"Unknown EC 0x{ec:02x}")
    details = []
    if ec in (0x24, 0x25): # Data abort
        dfsc = iss & 0x3f
        wnr = (iss >> 6) & 0x1
        s1ptw = (iss >> 7) & 0x1
        cm = (iss >> 8) & 0x1
        ea = (iss >> 9) & 0x1
        fnv = (iss >> 10) & 0x1
        set_val = (iss >> 11) & 0x3
        vncr = (iss >> 13) & 0x1
        ar = (iss >> 14) & 0x1
        sf = (iss >> 15) & 0x1
        details.append(f"WriteNotRead={'WRITE' if wnr else 'READ'}")
        dfsc_names = {
            0b000000: "Address size fault, level 0",
            0b000001: "Address size fault, level 1",
            0b000010: "Address size fault, level 2",
            0b000011: "Address size fault, level 3",
            0b000100: "Translation fault, level 0",
            0b000101: "Translation fault, level 1",
            0b000110: "Translation fault, level 2",
            0b000111: "Translation fault, level 3",
            0b001001: "Access flag fault, level 1",
            0b001010: "Access flag fault, level 2",
            0b001011: "Access flag fault, level 3",
            0b001101: "Permission fault, level 1",
            0b001110: "Permission fault, level 2",
            0b001111: "Permission fault, level 3",
            0b010000: "Synchronous External abort",
            0b010001: "Synchronous Tag Check Fault",
            0b010100: "Synchronous External abort on translation table walk, level 0",
            0b010101: "Synchronous External abort on translation table walk, level 1",
            0b010110: "Synchronous External abort on translation table walk, level 2",
            0b010111: "Synchronous External abort on translation table walk, level 3",
            0b100001: "Alignment fault",
        }
        details.append(f"DFSC: {dfsc_names.get(dfsc, f'0x{dfsc:02x}')}")
    elif ec in (0x20, 0x21): # Instruction abort
        ifsc = iss & 0x3f
        details.append(f"IFSC: 0x{ifsc:02x}")
    elif ec == 0x1a: # PAC fail
        pcode = iss & 0x3
        details.append(f"PCODE: {pcode}")
    
    return f"EC=0x{ec:02x} ({name}), IL={il}, ISS=0x{iss:07x} [{', '.join(details)}]"

def parse_reg(reg_name):
    try:
        val = int(gdb.parse_and_eval(f"${reg_name}"))
        return val & 0xffffffffffffffff
    except Exception:
        return None

def insert_verified_hbreak(addr, label):
    log(f"[GDB-PY] Inserting hardware breakpoint for {label} at 0x{addr:016x}...")
    bp_count_before = len(gdb.breakpoints()) if gdb.breakpoints() else 0
    try:
        gdb.execute(f"hbreak *0x{addr:x}")
    except gdb.error as e:
        log(f"[GDB-ERROR] gdb.execute(hbreak *0x{addr:x}) failed: {e}")
        raise
    
    bps = gdb.breakpoints()
    if not bps or len(bps) <= bp_count_before:
        raise RuntimeError(f"Breakpoint list did not increment when inserting {label} at 0x{addr:016x}")
    
    new_bp = bps[-1]
    log(f"[GDB-CONFIRMED] Breakpoint #{new_bp.number} inserted at 0x{addr:016x} ({label}), enabled={new_bp.enabled}")
    return new_bp

def main():
    init_logging()
    log("[GDB-PY] Initializing GDB session...")
    gdb.execute("set pagination off")
    gdb.execute("set confirm off")
    gdb.execute("set architecture aarch64")

    sock = "/tmp/openios_gdb_session.sock"
    log(f"[GDB-PY] Validating and connecting to gdbstub socket: {sock}...")
    try:
        gdb.execute(f"target remote {sock}")
    except gdb.error as e:
        log(f"[GDB-ERROR] Connection to gdbstub failed: {e}")
        sys.exit(1)

    inferior = gdb.selected_inferior()
    if not inferior or not inferior.is_valid():
        log("[GDB-ERROR] Connection validation failed: selected_inferior is invalid.")
        sys.exit(1)
    log(f"[GDB-PY] GDB connected successfully. Target inferior PID: {inferior.pid}")

    # Slid addresses (slide = +0x20000000)
    ADDR_RTBUDDY_START = 0xfffffff029b3d6bc
    ADDR_RTBUDDY_EXIT  = 0xfffffff029b3d7f8
    ADDR_EXCEPTION_VEC = 0xfffffff029db08a8
    ADDR_PANIC         = 0xfffffff02a5e5878  # Verified panic() entry

    log("[GDB-PY] Inserting verified hardware breakpoints while QEMU is paused (-S)...")
    bp_start = insert_verified_hbreak(ADDR_RTBUDDY_START, "RTBuddy::start entry")
    bp_exit  = insert_verified_hbreak(ADDR_RTBUDDY_EXIT,  "RTBuddy::start return")
    bp_exc   = insert_verified_hbreak(ADDR_EXCEPTION_VEC, "EL1 Sync Exception Vector (pre-sleh_synchronous)")
    bp_panic = insert_verified_hbreak(ADDR_PANIC,         "panic() entry")

    log("[GDB-PY] All breakpoints verified. Resuming guest execution via 'continue'...")

    rtbuddy_entered = False
    page_fault_count = 0

    while True:
        try:
            gdb.execute("continue")
        except gdb.error as e:
            log(f"[GDB-ERROR] continue interrupted with error: {e}")
            break

        cur_pc = parse_reg("pc")
        if cur_pc is None:
            log("[GDB-WARN] Unable to read PC after stop.")
            break

        if cur_pc == ADDR_RTBUDDY_START:
            rtbuddy_entered = True
            log(f"\n[EVENT] >>> HIT RTBuddy::start entry at PC = 0x{cur_pc:016x} <<<")
            log(f"        x0 (this) = 0x{parse_reg('x0'):016x}")
            log(f"        x1 (provider nub) = 0x{parse_reg('x1'):016x}")
            log(f"        LR = 0x{parse_reg('x30'):016x}")
            log("[EVENT] Execution entered RTBuddy::start. Continuing downstream initialization...")
            continue

        elif cur_pc == ADDR_RTBUDDY_EXIT:
            w0_val = parse_reg("w0")
            log(f"\n[EVENT] >>> RTBuddy::start COMPLETED SUCCESSFULLY! <<<")
            log(f"        PC = 0x{cur_pc:016x}")
            log(f"        Return value: w0 = {w0_val} ({'SUCCESS' if w0_val == 1 else 'FAILURE'})")
            break

        elif cur_pc == ADDR_EXCEPTION_VEC:
            esr_val = parse_reg("x1")
            far_val = parse_reg("x2")
            faulting_pc = parse_reg("x25")
            spsr_val = parse_reg("x4")
            saved_state = parse_reg("x0")

            # Check if benign demand-zero page fault or early-boot translation
            ec = (esr_val >> 26) & 0x3f if esr_val is not None else 0
            dfsc = (esr_val & 0x3f) if esr_val is not None else 0
            # DFSC 0x04..0x0f are normal translation/permission/access-flag faults
            is_vm_fault = (ec == 0x25 and 0x04 <= dfsc <= 0x0f)

            if is_vm_fault or not rtbuddy_entered:
                page_fault_count += 1
                if rtbuddy_entered or page_fault_count <= 5 or page_fault_count % 50 == 0:
                    phase = "INSIDE RTBUDDY" if rtbuddy_entered else "EARLY BOOT"
                    log(f"[BENIGN-PAGE-FAULT #{page_fault_count} ({phase})] Translation/permission fault level {dfsc & 3} at PC 0x{faulting_pc:016x}, FAR 0x{far_val:016x} -> continuing")
                continue

            # Non-benign or external exception trapped!
            log("\n=======================================================")
            log(f"[PRIMARY EXCEPTION CAPTURED BEFORE SECONDARY HANDLER!]")
            log("=======================================================")
            log(f"  Exception Vector PC: 0x{cur_pc:016x}")
            log(f"  Faulting PC (ELR_EL1 / x25): 0x{faulting_pc:016x} (unslid: 0x{faulting_pc - 0x20000000:016x})")
            log(f"  Faulting Addr (FAR_EL1 / x2): 0x{far_val:016x} (unslid: 0x{far_val - 0x20000000:016x})")
            log(f"  Syndrome (ESR_EL1 / x1): 0x{esr_val:08x}")
            log(f"  Decoded Syndrome: {decode_esr(esr_val)}")
            log(f"  Saved SPSR (SPSR_EL1 / x4): 0x{spsr_val:08x}")
            log(f"  Saved State Pointer (x0): 0x{saved_state:016x}")

            # Disassemble faulting instruction
            log(f"\n--- Disassembly at Faulting PC (0x{faulting_pc:x}) ---")
            try:
                log(gdb.execute(f"x/8i 0x{faulting_pc - 8:x}", to_string=True))
            except Exception as e:
                log(f"Disassembly error: {e}")

            # Physical address resolution
            log(f"\n--- Physical Address Resolution (monitor gva2gpa) ---")
            try:
                gpa_res = gdb.execute(f"monitor gva2gpa 0x{far_val:x}", to_string=True)
                log(f"  Virtual FAR 0x{far_val:x} -> Physical: {gpa_res.strip()}")
            except Exception as e:
                log(f"  gva2gpa failed: {e}")

            # Register dump
            log(f"\n--- GDB Registers at Exception ---")
            try:
                log(gdb.execute("info registers", to_string=True))
            except Exception as e:
                log(f"  info registers failed: {e}")

            # Frame pointer unwind from arm_saved_state64
            log(f"\n--- Kernel Frame Pointer Unwind ---")
            try:
                saved_fp = struct.unpack_from("<Q", inferior.read_memory(saved_state + 240, 8))[0]
                saved_lr = struct.unpack_from("<Q", inferior.read_memory(saved_state + 248, 8))[0]
                log(f"  Frame 0: PC = 0x{faulting_pc:016x} (unslid: 0x{faulting_pc - 0x20000000:016x})")
                log(f"  Frame 1: LR = 0x{saved_lr:016x} (unslid: 0x{saved_lr - 0x20000000:016x})  FP = 0x{saved_fp:016x}")
                fp = saved_fp
                for idx in range(2, 16):
                    if fp == 0 or fp < 0xffffffe000000000:
                        break
                    mem = inferior.read_memory(fp, 16)
                    next_fp, next_lr = struct.unpack("<QQ", mem)
                    log(f"  Frame {idx}: LR = 0x{next_lr:016x} (unslid: 0x{next_lr - 0x20000000:016x})  FP = 0x{next_fp:016x}")
                    if next_fp <= fp:
                        break
                    fp = next_fp
            except Exception as e:
                log(f"  Unwind error: {e}")

            log("[GDB-PY] Stopped before secondary exception processing. Evidence preserved.")
            break

        elif cur_pc == ADDR_PANIC:
            caller_lr = parse_reg("x30")
            panic_str_ptr = parse_reg("x0")
            log(f"\n[EVENT] >>> Stopped at panic() entry (PC = 0x{cur_pc:016x}) <<<")
            log(f"        Caller LR = 0x{caller_lr:016x} (unslid: 0x{caller_lr - 0x20000000:016x})")
            log(f"        panic string pointer (x0) = 0x{panic_str_ptr:016x}")
            try:
                pstr = gdb.execute("x/s $x0", to_string=True)
                log(f"        panic string: {pstr.strip()}")
            except Exception:
                pass
            break

        else:
            log(f"[GDB-PY] Stopped at unexpected PC = 0x{cur_pc:016x}")
            break

    log("\n[GDB-PY] Capture worker session finished cleanly. Exiting GDB.")
    try:
        gdb.execute("quit")
    except Exception:
        pass

if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        log(f"[GDB-FATAL] Exception in worker: {err}")
        traceback.print_exc()
