# core/tsk_wrapper.py
import subprocess
import os
import re
import tempfile
import binascii

class TSKWrapper:
    def __init__(self):
        self.current_image = None
        self.current_offset = 0
        
    def check_tsk_installed(self):
        """Verify that Sleuth Kit tools are available"""
        try:
            subprocess.run(['fls', '-V'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
            
    def load_image(self, image_path):
        """Load a disk image and get partition info using mmls"""
        if not os.path.exists(image_path):
            raise Exception(f"Image not found: {image_path}")
            
        if not self.check_tsk_installed():
            raise Exception("The Sleuth Kit (TSK) is not installed or not in PATH. Please install it first.")
            
        self.current_image = image_path
        
        result = {
            'image_path': image_path,
            'partitions': [],
            'partition_table': 'Unknown'
        }
        
        # Run mmls to detect partitions
        try:
            output = subprocess.run(
                ['mmls', image_path], 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            # Parse mmls output
            lines = output.stdout.split('\n')
            partition_re = re.compile(r'^\s*(\d+):\s+(\w+)\s+(\d+)\s+(\d+)\s+(\d+)')
            
            for line in lines:
                match = partition_re.match(line)
                if match:
                    idx = int(match.group(1))
                    typ = match.group(2)
                    if typ not in ['Unallocated', 'Meta', 'Table']:
                        offset = int(match.group(4)) * 512  # sectors to bytes
                        result['partitions'].append({
                            'index': idx,
                            'type': typ,
                            'offset': offset,
                            'start_sector': int(match.group(4)),
                            'length': int(match.group(5))
                        })
                        
            # Detect partition table type
            if 'EFI GPT' in output.stdout:
                result['partition_table'] = 'GPT'
            elif 'DOS' in output.stdout:
                result['partition_table'] = 'MBR'
                
        except subprocess.CalledProcessError as e:
            # Maybe it's a raw filesystem without partition table
            if 'Cannot determine partition type' in e.stderr:
                # Treat as raw filesystem
                result['partitions'] = [{
                    'index': 0,
                    'type': 'Raw FS',
                    'offset': 0,
                    'start_sector': 0,
                    'length': 0
                }]
            else:
                raise Exception(f"mmls error: {e.stderr}")
                
        return result
        
    def list_directory(self, image_path, offset=0, inode=None):
        """List directory contents using fls"""
        self.current_offset = offset
        sector_offset = offset // 512
        
        cmd = ['fls', '-o', str(sector_offset), image_path]
        if inode:
            cmd.extend([str(inode)])
            
        try:
            output = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return self._parse_fls_output(output.stdout)
        except subprocess.CalledProcessError as e:
            return {'error': e.stderr}
    
    def get_deleted_files(self, image_path, offset=0):
        """Get only deleted files using fls -d"""
        sector_offset = offset // 512
        cmd = ['fls', '-d', '-o', str(sector_offset), image_path]
        
        try:
            output = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return self._parse_fls_output(output.stdout)
        except subprocess.CalledProcessError as e:
            return {'error': e.stderr}
    
    def get_file_metadata(self, image_path, offset, inode):
        """Get file metadata using istat"""
        sector_offset = offset // 512
        cmd = ['istat', '-o', str(sector_offset), image_path, str(inode)]
        
        try:
            output = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return output.stdout
        except subprocess.CalledProcessError as e:
            return f"Error getting metadata: {e.stderr}"
    
    def recover_file(self, image_path, offset, inode, output_path):
        """Recover a deleted or existing file using icat"""
        sector_offset = offset // 512
        cmd = ['icat', '-o', str(sector_offset), image_path, str(inode)]
        
        try:
            with open(output_path, 'wb') as outfile:
                result = subprocess.run(cmd, capture_output=True, check=True)
                outfile.write(result.stdout)
            return True, f"File recovered to: {output_path}"
        except subprocess.CalledProcessError as e:
            return False, f"Recovery failed: {e.stderr}"
    
    def get_hex_view(self, image_path, offset, inode, block_size=512, num_blocks=4):
        """Get hexadecimal view of file blocks using icat and hexdump"""
        sector_offset = offset // 512
        cmd = ['icat', '-o', str(sector_offset), image_path, str(inode)]
        
        try:
            result = subprocess.run(cmd, capture_output=True, check=True)
            data = result.stdout[:block_size * num_blocks]  # Limit to prevent memory issues
            
            # Format as hex
            hex_output = []
            for i in range(0, len(data), 16):
                chunk = data[i:i+16]
                hex_part = ' '.join(f'{b:02x}' for b in chunk)
                ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                hex_output.append(f'{i:08x}  {hex_part:<48}  {ascii_part}')
            
            return '\n'.join(hex_output)
        except subprocess.CalledProcessError as e:
            return f"Error reading hex data: {e.stderr}"
    
    def search_hex_pattern(self, image_path, offset, pattern_hex):
        """Search for hex pattern in the filesystem"""
        # This uses blkls to search raw data (simplified version)
        sector_offset = offset // 512
        pattern_bytes = bytes.fromhex(pattern_hex.replace(' ', ''))
        
        # Use dd + grep style search (basic implementation)
        cmd = f"blkls -o {sector_offset} {image_path} 2>/dev/null | hexdump -C | grep -i '{pattern_hex}'"
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout if result.stdout else "Pattern not found"
        except Exception as e:
            return f"Search error: {str(e)}"
        
    def _parse_fls_output(self, output):
        """Parse fls output into structured data"""
        files = []
        lines = output.split('\n')
        for line in lines:
            if not line.strip():
                continue
            # Typical fls line: "r/r 1234:  file.txt"
            if ':' in line:
                parts = line.split(':', 1)
                meta_part = parts[0].strip()
                name = parts[1].strip() if len(parts) > 1 else ''
                
                # Parse permission and inode
                meta_parts = meta_part.split()
                if len(meta_parts) >= 2:
                    perm = meta_parts[0]
                    inode = meta_parts[1]
                    
                    # Determine if deleted (look for 'd' or alloc flag)
                    is_deleted = '*' in perm or 'd' in perm or 'u' in perm.lower()
                    
                    # Determine file type
                    if 'r/r' in perm:
                        file_type = "📄 File"
                    elif 'd/d' in perm:
                        file_type = "📁 Directory"
                    elif 'l/l' in perm:
                        file_type = "🔗 Link"
                    else:
                        file_type = "❓ Unknown"
                    
                    files.append({
                        'name': name,
                        'inode': inode,
                        'permissions': perm,
                        'deleted': is_deleted,
                        'type': file_type
                    })
        return files
