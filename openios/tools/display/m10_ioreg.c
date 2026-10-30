/*
 * Enhanced IORegistry diagnostic for OpeniOS Stage A (M10.2 -> SpringBoard).
 *
 * Inspects both gIOServicePlane ("IOService") and gIODTPlane ("IODeviceTree")
 * to definitively analyze device tree topology, provider/child relationships,
 * registry entry IDs, and exact placement of iop-dcp-nub.
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
extern kern_return_t IORegistryEntryGetParentIterator(io_registry_entry_t entry,
                                                      const char *plane,
                                                      io_iterator_t *iterator);
extern kern_return_t IORegistryEntryGetRegistryEntryID(io_registry_entry_t entry,
                                                       uint64_t *entryID);
extern io_registry_entry_t IORegistryEntryFromPath(mach_port_t master_port,
                                                  const char *path);
extern kern_return_t IOObjectGetClass(io_object_t object, char *className);
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

static void emit_hex64(uint64_t val)
{
    char buf[19];
    static const char hex[] = "0123456789abcdef";
    int i;
    buf[0] = '0';
    buf[1] = 'x';
    for (i = 0; i < 16; ++i) {
        buf[2 + i] = hex[(val >> (60 - i * 4)) & 0xf];
    }
    buf[18] = '\0';
    emit(buf);
}

static int same_text(const char *left, const char *right)
{
    while (*left != '\0' && *left == *right) {
        ++left;
        ++right;
    }
    return *left == *right;
}

static int has_prefix(const char *text, const char *prefix)
{
    while (*prefix != '\0') {
        if (*text != *prefix) return 0;
        ++text;
        ++prefix;
    }
    return 1;
}

static int contains_text(const char *str, const char *sub)
{
    unsigned long i, j;
    if (!sub[0]) return 1;
    for (i = 0; str[i] != '\0'; ++i) {
        for (j = 0; sub[j] != '\0'; ++j) {
            if (str[i + j] != sub[j]) break;
        }
        if (sub[j] == '\0') return 1;
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

static void emit_relations(io_registry_entry_t entry, const char *plane, int is_children)
{
    io_iterator_t iterator = 0;
    io_object_t related;
    char name[128];
    char path[512];
    char class_name[128];
    uint64_t entry_id = 0;
    kern_return_t kr;

    if (is_children) {
        kr = IORegistryEntryGetChildIterator(entry, plane, &iterator);
    } else {
        kr = IORegistryEntryGetParentIterator(entry, plane, &iterator);
    }

    if (kr != 0) {
        emit(is_children ? "    [children-error]\n" : "    [parents-error]\n");
        return;
    }

    while ((related = IOIteratorNext(iterator)) != 0) {
        name[0] = '\0';
        path[0] = '\0';
        class_name[0] = '\0';
        entry_id = 0;

        (void)IORegistryEntryGetNameInPlane(related, plane, name);
        (void)IORegistryEntryGetPath(related, plane, path);
        (void)IOObjectGetClass(related, class_name);
        (void)IORegistryEntryGetRegistryEntryID(related, &entry_id);

        emit(is_children ? "    CHILD in " : "    PARENT in ");
        emit(plane);
        emit(": name=");
        emit(name[0] ? name : "<unnamed>");
        emit(" class=");
        emit(class_name[0] ? class_name : "<unknown>");
        emit(" id=");
        emit_hex64(entry_id);
        emit(" path=");
        emit(path[0] ? path : "<no-path>");
        emit("\n");

        (void)IOObjectRelease(related);
    }
    (void)IOObjectRelease(iterator);
}

static void inspect_entry_details(io_registry_entry_t entry, const char *plane_context)
{
    char name[128] = {0};
    char path_svc[512] = {0};
    char path_dt[512] = {0};
    char class_name[128] = {0};
    uint64_t entry_id = 0;

    (void)IORegistryEntryGetNameInPlane(entry, plane_context, name);
    (void)IORegistryEntryGetPath(entry, "IOService", path_svc);
    (void)IORegistryEntryGetPath(entry, "IODeviceTree", path_dt);
    (void)IOObjectGetClass(entry, class_name);
    (void)IORegistryEntryGetRegistryEntryID(entry, &entry_id);

    emit("=== DETAILS FOR: ");
    emit(name[0] ? name : "<unnamed>");
    emit(" ===\n");
    emit("  EntryID: "); emit_hex64(entry_id); emit("\n");
    emit("  IOObjectGetClass: "); emit(class_name[0] ? class_name : "<unknown>"); emit("\n");
    emit("  IOService Path: "); emit(path_svc[0] ? path_svc : "<none>"); emit("\n");
    emit("  IODeviceTree Path: "); emit(path_dt[0] ? path_dt : "<none>"); emit("\n");
    emit("  compatible: "); emit_property(entry, "compatible"); emit("\n");
    emit("  IOClass: "); emit_property(entry, "IOClass"); emit("\n");
    emit("  IOProviderClass: "); emit_property(entry, "IOProviderClass"); emit("\n");
    emit("  device_type: "); emit_property(entry, "device_type"); emit("\n");
    emit("  AAPL,phandle: "); emit_property(entry, "AAPL,phandle"); emit("\n");
    emit("  role: "); emit_property(entry, "role"); emit("\n");

    emit("  -- IOService Parents & Children --\n");
    emit_relations(entry, "IOService", 0);
    emit_relations(entry, "IOService", 1);

    emit("  -- IODeviceTree Parents & Children --\n");
    emit_relations(entry, "IODeviceTree", 0);
    emit_relations(entry, "IODeviceTree", 1);
}

int main(void)
{
    io_iterator_t iterator = 0;
    io_object_t object;
    char name[128];
    char path[512];
    char class_name[128];
    uint64_t entry_id;

    emit("OPENIOS_STAGE_A_BEGIN\n");

    /* 1. Walk IODeviceTree plane */
    emit("\n--- SECTION 1: IODeviceTree PLANE DUMP ---\n");
    if (IORegistryCreateIterator(0, "IODeviceTree", kIORegistryIterateRecursively, &iterator) == 0) {
        while ((object = IOIteratorNext(iterator)) != 0) {
            name[0] = '\0';
            path[0] = '\0';
            class_name[0] = '\0';
            entry_id = 0;
            (void)IORegistryEntryGetNameInPlane(object, "IODeviceTree", name);
            (void)IORegistryEntryGetPath(object, "IODeviceTree", path);
            (void)IOObjectGetClass(object, class_name);
            (void)IORegistryEntryGetRegistryEntryID(object, &entry_id);

            /* Report all arm-io children or display/dcp/iop related */
            if (contains_text(path, "dcp") || contains_text(path, "disp") ||
                contains_text(path, "iop") || contains_text(path, "asc") ||
                contains_text(path, "dart") || contains_text(path, "arm-io") ||
                same_text(name, "arm-io")) {
                emit("DT_NODE name="); emit(name);
                emit(" id="); emit_hex64(entry_id);
                emit(" class="); emit(class_name);
                emit(" path="); emit(path);
                emit(" compat="); emit_property(object, "compatible");
                emit("\n");

                if (contains_text(name, "dcp") || contains_text(name, "iop-dcp-nub")) {
                    inspect_entry_details(object, "IODeviceTree");
                }
            }
            (void)IOObjectRelease(object);
        }
        (void)IOObjectRelease(iterator);
    } else {
        emit("ERROR: failed to create IODeviceTree iterator\n");
    }

    /* 2. Walk IOService plane */
    emit("\n--- SECTION 2: IOService TARGET INSPECTION ---\n");
    if (IORegistryCreateIterator(0, "IOService", kIORegistryIterateRecursively, &iterator) == 0) {
        while ((object = IOIteratorNext(iterator)) != 0) {
            name[0] = '\0';
            (void)IORegistryEntryGetNameInPlane(object, "IOService", name);

            if (same_text(name, "AppleASCWrapV6") ||
                same_text(name, "AppleA7IOPNub") ||
                same_text(name, "RTBuddy") ||
                same_text(name, "AppleDCPExpert") ||
                same_text(name, "AppleCLCD2") ||
                same_text(name, "dcp") ||
                same_text(name, "disp0") ||
                same_text(name, "iop-dcp-nub")) {
                inspect_entry_details(object, "IOService");
            }
            (void)IOObjectRelease(object);
        }
        (void)IOObjectRelease(iterator);
    } else {
        emit("ERROR: failed to create IOService iterator\n");
    }

    /* 3. Direct lookup by paths */
    emit("\n--- SECTION 3: DIRECT PATH LOOKUPS ---\n");
    {
        static const char *const direct_paths[] = {
            "IODeviceTree:/arm-io/dcp",
            "IODeviceTree:/arm-io/dcp/iop-dcp-nub",
            "IODeviceTree:/arm-io/dcp0-expert",
            "IODeviceTree:/arm-io/disp0",
            "IOService:/AppleARMPE/arm-io@10F00000/AppleT812xIO/dcp@32C00000",
            "IOService:/AppleARMPE/arm-io@10F00000/AppleT812xIO/dcp@32C00000/AppleASCWrapV6",
        };
        unsigned long i;
        for (i = 0; i < sizeof(direct_paths) / sizeof(direct_paths[0]); ++i) {
            io_registry_entry_t entry = IORegistryEntryFromPath(0, direct_paths[i]);
            emit("LOOKUP "); emit(direct_paths[i]);
            if (entry != 0) {
                emit(" => FOUND (entry handle ");
                emit_hex64(entry);
                emit(")\n");
                inspect_entry_details(entry, "IOService");
                (void)IOObjectRelease(entry);
            } else {
                emit(" => NOT FOUND\n");
            }
        }
    }

    emit("\nOPENIOS_STAGE_A_DONE\n");
    return 0;
}
