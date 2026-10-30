/* Minimal loader/signing smoke test; deliberately not an IORegistry utility. */
.section __TEXT,__text,regular,pure_instructions
.p2align 2
.globl _main
_main:
    adrp    x1, message@PAGE
    add     x1, x1, message@PAGEOFF
    mov     x0, #1
    mov     x2, #message_len
    mov     x16, #4
    movk    x16, #0x20, lsl #16
    svc     #0x80
    mov     x0, #0
    mov     x16, #1
    movk    x16, #0x20, lsl #16
    svc     #0x80
message:
    .ascii "openios-m8-smoke: signed Mach-O diagnostic\\n"
.set message_len, . - message
