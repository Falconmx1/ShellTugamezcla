# 🗑️ File Recovery Guide for ShellTuga

## How Deleted File Recovery Works

When you delete a file in most filesystems, the data isn't immediately erased. Instead:
- The **inode** is marked as "free"
- The filename is removed from the directory
- The actual data blocks remain until overwritten

ShellTuga uses **The Sleuth Kit** tools to recover these files:

### Recovery Methods

1. **icat** - Extracts file data by inode number
2. **fls -d** - Lists only deleted files
3. **istat** - Shows metadata to confirm recoverability

### Step-by-Step Recovery

1. Load your disk image
2. Go to "🗑️ Deleted Files" tab
3. Browse red-colored deleted entries
4. Right-click or use Recover button
5. Save to a safe location (different drive!)

### Tips for Better Recovery

✅ **Act quickly** - More usage = higher chance of overwrite  
✅ **Recover to different drive** - Never write to the evidence image  
✅ **Check metadata first** - See if blocks are still allocated  
✅ **Carve manually** - Use hex search for file signatures (JPEG: FF D8, PDF: 25 50 44 46)

### File Signatures (Magic Bytes)

| File Type | Hex Signature | ASCII |
|-----------|--------------|-------|
| JPEG | `FF D8 FF` | ÿØÿ |
| PNG | `89 50 4E 47` | .PNG |
| PDF | `25 50 44 46` | %PDF |
| ZIP | `50 4B 03 04` | PK.. |
| ELF | `7F 45 4C 46` | .ELF |

### Limitations

❌ Fragmented files may recover partially  
❌ Zeroed/TRIM commands destroy data  
❌ Encrypted drives need decryption first  
❌ SSD garbage collection may wipe quickly

---

**Remember:** Always work on a forensic copy, never on original evidence!
