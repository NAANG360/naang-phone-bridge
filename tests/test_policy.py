import unittest
from bridge.phone_bridge import blocked

class PolicyTests(unittest.TestCase):
    def test_blocks_recursive_root_delete(self): self.assertTrue(blocked('rm -rf /'))
    def test_blocks_mkfs(self): self.assertTrue(blocked('mkfs.ext4 /dev/block/sda'))
    def test_blocks_bootloader_reboot(self): self.assertTrue(blocked('reboot bootloader'))
    def test_allows_read_only_commands(self):
        for cmd in ('getprop','id','ps -A','logcat -d -t 20'): self.assertFalse(blocked(cmd))

if __name__ == '__main__': unittest.main()
