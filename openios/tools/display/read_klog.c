#include <stdint.h>
#include <stddef.h>

extern int sysctlbyname(const char *name, void *oldp, size_t *oldlenp, void *newp, size_t newlen);
extern long write(int fd, const void *buffer, unsigned long length);

int main(void)
{
    static char buf[262144];
    size_t len = sizeof(buf);
    
    if (sysctlbyname("kern.msgbuf", buf, &len, 0, 0) == 0 && len > 0) {
        (void)write(1, "=== KLOG BEGIN ===\n", 19);
        (void)write(1, buf, len);
        (void)write(1, "\n=== KLOG END ===\n", 18);
    } else {
        (void)write(1, "ERROR: sysctlbyname kern.msgbuf failed\n", 39);
    }
    return 0;
}
