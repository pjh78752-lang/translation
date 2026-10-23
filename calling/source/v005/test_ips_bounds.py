"""Regression checks for composed IPS records surviving a target-size shrink."""
import unittest
from build_v005 import apply_ips,normalize_ips

def record(offset,data):
    return offset.to_bytes(3,'big')+len(data).to_bytes(2,'big')+data

def patch(records,target):
    return b'PATCH'+b''.join(records)+b'EOF'+target.to_bytes(3,'big')

def strict_apply(original,ips,target):
    """The Windows installer's fixed-size allocation and bounds contract."""
    out=bytearray(original[:target]).ljust(target,b'\0');pos=5
    while ips[pos:pos+3]!=b'EOF':
        offset=int.from_bytes(ips[pos:pos+3],'big');size=int.from_bytes(ips[pos+3:pos+5],'big');pos+=5
        if offset+size>target:raise ValueError('IPS record is out of bounds')
        out[offset:offset+size]=ips[pos:pos+size];pos+=size
    return bytes(out)

class ShrinkRegression(unittest.TestCase):
    def test_shrink_reproduces_installer_error_then_preserves_result(self):
        p=patch([record(3,b'abcdefg'),record(3,b'XYZ')],6)
        with self.assertRaisesRegex(ValueError,'out of bounds'):strict_apply(b'0123456789',p,6)
        self.assertEqual(strict_apply(b'0123456789',normalize_ips(p),6),b'012XYZ')

    def test_later_overlapping_write_wins(self):
        p=patch([record(1,b'aaaaaa'),record(3,b'XYZ')],8)
        self.assertEqual(strict_apply(b'01234567',normalize_ips(p),8),b'0aaXYZa7')

    def test_untouched_bytes_remain_input_dependent(self):
        p=patch([record(1,b'X'),record(8,b'gone')],4)
        self.assertEqual(strict_apply(b'abcdefgh',normalize_ips(p),4),b'aXcd')
        self.assertEqual(strict_apply(b'01234567',normalize_ips(p),4),b'0X23')

    def test_normalization_is_repeatable(self):
        p=patch([record(0,b'abcdef'),record(2,b'XYZ')],5)
        n=normalize_ips(p)
        self.assertEqual(normalize_ips(n),n)
        self.assertEqual(apply_ips(b'123456',p),strict_apply(b'123456',n,5))

if __name__=='__main__':unittest.main()
