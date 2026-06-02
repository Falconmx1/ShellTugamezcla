# core/tsk_wrapper.py
import subprocess
import os
import re

class TSKWrapper:
    def __init__(self):
        self.current_image = None
        
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
        cmd = ['fls', '-o', str(offset // 512), image_path]
        if inode:
            cmd.extend(['-f', str(inode)])
            
        try:
            output = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return self._parse_fls_output(output.stdout)
        except subprocess.CalledProcessError as e:
            return {'error': e.stderr}
            
    def _parse_fls_output(self, output):
        """Parse fls output into structured data"""
        files = []
        lines = output.split('\n')
        for line in lines:
            if not line.strip():
                continue
            # Typical fls line: "r/r 1234: file.txt"
            parts = line.split(':')
            if len(parts) >= 2:
                meta_part = parts[0].strip()
                name = parts[1].strip()
                
                # Parse permission and inode
                meta_parts = meta_part.split()
                if len(meta_parts) >= 2:
                    perm = meta_parts[0]
                    inode = meta_parts[1]
                    
                    # Determine if deleted (look for 'd' or alloc flag)
                    is_deleted = '*' in perm or 'd' in perm
                    
                    files.append({
                        'name': name,
                        'inode': inode,
                        'permissions': perm,
                        'deleted': is_deleted
                    })
        return files
