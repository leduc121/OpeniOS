/*
 * Read-only IORegistry diagnostic for the OpeniOS restore environment.
 *
 * The function contracts and iterator flag below are from Apple's
 * open-source IOKitUser/IOKitLib.h.  The function symbols were additionally
 * verified in the matching 23G71 IOKit framework before this file was added.
 * This intentionally avoids CoreFoundation property serialization and
 * ncurses, neither of which is needed to enumerate published IOService nodes.
 */
#include <stdint.h>

typedef uint32_t mach_port_t;
typedef uint32_t kern_return_t;
typedef uint32_t io_object_t;
typedef io_object_t io_iterator_t;
typedef io_object_t io_registry_entry_t;
typedef uint32_t IOOptionBits;

enum {
    kIORegistryIterateRecursively = 0x00000001,
};

extern kern_return_t IORegistryCreateIterator(mach_port_t master_port,
                                               const char *plane,
                                               IOOptionBits options,
                                               io_iterator_t *iterator);
extern io_object_t IOIteratorNext(io_iterator_t iterator);
extern kern_return_t IORegistryEntryGetNameInPlane(io_registry_entry_t entry,
                                                    const char *plane,
                                                    char *name);
extern kern_return_t IORegistryEntryGetPath(io_registry_entry_t entry,
                                            const char *plane,
                                            char *path);
extern kern_return_t IORegistryEntryGetProperty(io_registry_entry_t entry,
                                                const char *property_name,
                                                void *buffer,
                                                uint32_t *size);
extern kern_return_t IORegistryEntryGetChildIterator(io_registry_entry_t entry,
                                                     const char *plane,
                                                     io_iterator_t *iterator);
extern kern_return_t IOObjectRelease(io_object_t object);
extern long write(int fd, const void *buffer, unsigned long length);

static unsigned long text_length(const char *text)
{
    unsigned long length = 0;

    while (text[length] != '\0') {
        ++length;
    }
    return length;
}

static void emit(const char *text)
{
    (void)write(1, text, text_length(text));
}

static int same_text(const char *left, const char *right)
{
    while (*left != '\0' && *left == *right) {
        ++left;
        ++right;
    }
    return *left == *right;
}

static int is_target(const char *name)
{
    static const char *const targets[] = {
        "AppleASCWrapV6",
        "AppleA7IOPNub",
        "RTBuddy",
        "AppleDCPExpert",
        "AppleCLCD2",
        "IOMobileFramebuffer",
        "dart-disp0",
        "dart-dcp",
        "dart-dispgrt",
        "dcp",
        "disp0",
    };
    unsigned long i;

    for (i = 0; i < sizeof(targets) / sizeof(targets[0]); ++i) {
        if (same_text(name, targets[i])) {
            return 1;
        }
    }
    return 0;
}

static void emit_property(io_registry_entry_t entry, const char *property)
{
    char value[512];
    uint32_t size = sizeof(value) - 1;
    uint32_t i;

    if (IORegistryEntryGetProperty(entry, property, value, &size) != 0
        || size == 0 || size >= sizeof(value)) {
        emit("<unavailable>");
        return;
    }
    value[size] = '\0';
    for (i = 0; i < size; ++i) {
        if (value[i] == '\0') {
            value[i] = '|';
        } else if ((unsigned char)value[i] < 0x20 ||
                   (unsigned char)value[i] > 0x7e) {
            value[i] = '?';
        }
    }
    emit(value);
}

static void emit_direct_children(io_registry_entry_t entry, const char *plane)
{
    io_iterator_t iterator = 0;
    io_object_t child;
    char name[128];
    char path[512];

    if (IORegistryEntryGetChildIterator(entry, plane, &iterator) != 0) {
        emit("OPENIOS_IOREG_CHILD_ITERATOR_ERROR\n");
        return;
    }
    while ((child = IOIteratorNext(iterator)) != 0) {
        name[0] = '\0';
        path[0] = '\0';
        (void)IORegistryEntryGetNameInPlane(child, plane, name);
        (void)IORegistryEntryGetPath(child, plane, path);
        emit("OPENIOS_IOREG_CHILD name=");
        emit(name[0] != '\0' ? name : "<name-unavailable>");
        emit(" path=");
        emit(path[0] != '\0' ? path : "<path-unavailable>");
        emit(" class=");
        emit_property(child, "IOClass");
        emit(" provider=");
        emit_property(child, "IOProviderClass");
        emit(" compatible=");
        emit_property(child, "compatible");
        emit("\n");
        (void)IOObjectRelease(child);
    }
    (void)IOObjectRelease(iterator);
}

int main(void)
{
    static const char plane[] = "IOService";
    io_iterator_t iterator = 0;
    io_object_t object;
    unsigned long total = 0;
    unsigned long targets = 0;
    char name[128];
    char path[512];

    emit("OPENIOS_IOREG_BEGIN\n");
    if (IORegistryCreateIterator(0, plane, kIORegistryIterateRecursively,
                                 &iterator) != 0) {
        emit("OPENIOS_IOREG_ITERATOR_ERROR\n");
        return 2;
    }

    while ((object = IOIteratorNext(iterator)) != 0) {
        ++total;
        name[0] = '\0';
        path[0] = '\0';
        (void)IORegistryEntryGetNameInPlane(object, plane, name);
        if (is_target(name)) {
            (void)IORegistryEntryGetPath(object, plane, path);
            emit("OPENIOS_IOREG_TARGET name=");
            emit(name);
            emit(" path=");
            emit(path[0] != '\0' ? path : "<path-unavailable>");
            emit(" compatible=");
            emit_property(object, "compatible");
            emit(" class=");
            emit_property(object, "IOClass");
            emit(" provider=");
            emit_property(object, "IOProviderClass");
            emit("\n");
            if (same_text(name, "AppleASCWrapV6")) {
                emit_direct_children(object, plane);
            }
            ++targets;
        }
        (void)IOObjectRelease(object);
    }
    (void)IOObjectRelease(iterator);

    emit("OPENIOS_IOREG_DONE targets=");
    /* The fixed text keeps this minimal binary dependency-free. */
    emit(targets == 0 ? "0" : "nonzero");
    emit(" entries=");
    emit(total == 0 ? "0" : "nonzero");
    emit("\n");
    return 0;
}
