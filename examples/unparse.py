import sys
from ftemplatemodules import unparse
import argparse


def doArgs():
    args = argparse.ArgumentParser(
        description="Transform .ftmpl type file to .py type file")

    args.add_argument('-i', '--infile', dest='infile',
                      type=argparse.FileType('rt'), default=sys.stdin,
                      help='Input file')
    args.add_argument('-o', '--outfile', dest='outfile',
                      type=argparse.FileType('wt'), default=sys.stdout,
                      help='Output File')

    return args.parse_args()


def main():
    args = doArgs()
    args.outfile.write(unparse(args.infile))


if __name__ == "__main__":
    main()
