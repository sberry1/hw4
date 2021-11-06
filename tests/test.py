#!/usr/bin/env python

import os
import os.path
import tempfile
import subprocess
import time
import signal
import re
import sys
import shutil
import decode_out as dec
import csv
import abc

file_locations = os.path.expanduser(os.getcwd())
#logisim_location = os.path.join(os.getcwd(),"logisim.jar")
logisim_location = "logisim.jar"


class TestCase():
  """
      Runs specified circuit file and compares output against the provided reference trace file.
  """

  def __init__(self, circfile, expected):
    self.circfile  = circfile
    self.expected = expected

  def __call__(self, typ):
    oformat = dec.get_test_format(typ)
    if not oformat:
        print("CANNOT format test type")
        return (False, "Error in the test")

    try:
        if not isinstance(self.expected, list):
            # it is a file so parse it
            self.expected = [x for x in ReferenceFileParser(oformat, self.expected).outputs()]
        else:
            [oformat.validate(x) for x in self.expected]
    except dec.OutputFormatException as e:
        print("Error in formatting of expected output:")
        print("\t", e)
        return (False, "Error in the test")

    output = tempfile.TemporaryFile(mode='r+')
    command = ["java","-jar",logisim_location,"-tty","table", self.circfile]
    proc = subprocess.Popen(command,
                            stdin=open(os.devnull),
                            stdout=subprocess.PIPE, text=True)
    try:
      debug_buffer = [] 
      passed = compare_unbounded(proc.stdout,self.expected, oformat, debug_buffer)
    except dec.OutputFormatException as e:
        print("Error in formatting of Logisim output:")
        print("\t", e)
        return (False, "Error in the test")
    finally:
      os.kill(proc.pid,signal.SIGTERM)
    if passed:
      return (True, "Matched expected output")
    else:
      print("Format is student then expected")
      wtr = csv.writer(sys.stdout, delimiter='\t')
      oformat.header(wtr)
      for row in debug_buffer:
        wtr.writerow(['{0:x}'.format(b) for b in row[0]])
        wtr.writerow(['{0:x}'.format(b) for b in row[1]])

      return (False, "Did not match expected output")

def compare_unbounded(student_out, expected, oformat, debug):
  parser = OutputProvider(oformat)
  for i in range(0, len(expected)):
    line1 = student_out.readline()
    values_student_parsed = parser.parse_line(line1.rstrip())

    debug.append((values_student_parsed, expected[i]))

    if values_student_parsed != expected[i]:
      return False

  return True

def run_tests(tests):
  # actual submission testing code
  print("Testing files...")
  tests_passed = 0
  tests_failed = 0

  for description,test,typ in tests:
    test_passed, reason = test(typ)
    if test_passed:
      print("\tPASSED test: %s" % description)
      tests_passed += 1
    else:
      print("\tFAILED test: %s (%s)" % (description, reason))
      tests_failed += 1
  
  print("Passed %d/%d tests" % (tests_passed, (tests_passed + tests_failed)))

class OutputProvider(object):
    def __init__(self, format):
        self.format = format

    @abc.abstractmethod
    def outputs(self):
        pass
    
    def parse_line(self, line):
        value_strs = line.split('\t')   
        values_bin = [''.join(v.split(' ')) for v in value_strs] 
        try:
            values = [int(v, 2) for v in values_bin]
        except ValueError as e:
            raise dec.OutputFormatException("non-integer in {}".format(values_bin))
        self.format.validate(values)
        return values

class ReferenceFileParser(OutputProvider):
    def __init__(self, format, filename=None):
        self.f = filename
        super(ReferenceFileParser, self).__init__(format)

    def outputs(self):
        assert self.f is not None, "cannot use outputs if no filename given"
        with open(self.f, 'r') as inp:
            for line in inp.readlines():
                values = self.parse_line(line)
                yield values 

tests = [
  ("ALU add (with overflow) test",
        TestCase(os.path.join(file_locations,'alu-add.circ'),
                 [[0, 0b0000, 0x7659035D],
                  [1, 0b1001, 0x87A08D79],
                  [2, 0b1001, 0x80000000],
                  [3, 0b0100, 0x00000000],
                  [4, 0b0110, 0x00000000],
                  [5, 0b0010, 0x00000227],
                  [6, 0b0011, 0x70000203],
                  [7, 0b1010, 0xFFFFFEFF],
                  [8, 0b0100, 0x00000000]]), "alu"),
  ("ALU arithmetic right shift test",
        TestCase(os.path.join(file_locations,'alu-asr.circ'),
                [[0, 0b1000, 0xF7AB6FBB],
                 [1, 0b1000, 0xFFFFFC00],
                 [2, 0b0100,0x00000000],
                 [3, 0b1000,0xFEEDF00D],
                 [4, 0b0100, 0x00000000]]), "alu"),
  ("ALU Control Basic Data-processing Instructions Test",
    TestCase(os.path.join(file_locations, 'alu-control-basic-data-processing-test.circ'),
        [[0, 0],
         [1, 2],
         [2, 8],
         [3, 7],
         [4, 1],
         [5, 3]]), "alu-control"),
  ("ALU Control Shifts Test",
    TestCase(os.path.join(file_locations, 'alu-control-shifts-test.circ'),
        [[0, 4],
         [1, 5],
         [2, 6]]), "alu-control"),
  ("ALU Control CMP Test",
    TestCase(os.path.join(file_locations, 'alu-control-cmp-test.circ'),
        [[0, 8]]), "alu-control"),
  ("ALU Control B Test",
    TestCase(os.path.join(file_locations, 'alu-control-b-test.circ'),
        [[0, 7]]), "alu-control"),
  ("ALU Control ldr/str Test",
    TestCase(os.path.join(file_locations, 'alu-control-ldr-str-test.circ'),
        [[0, 7],
         [1, 7],
         [2, 7],
         [3, 7]]), "alu-control")
]

if __name__ == '__main__':
  run_tests(tests)
