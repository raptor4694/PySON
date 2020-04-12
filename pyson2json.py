import json, pyson
import os.path as path
import argparse

def main(args=None):
    """usage: pyson2json.py [-h] [-quiet] [--stop-on-error] [--print-traceback]
                     [--allow-inf-nan]
                     FILE [FILE ...]

    Convert a PySON file to a JSON file

    positional arguments:
      FILE               The files to convert

    optional arguments:
      -h, --help         show this help message and exit
      -quiet             Don't print extra information while converting files
      --stop-on-error    Halt execution upon errors instead of skipping the file
      --print-traceback  Print full traceback on error
      --allow-inf-nan    Allows Infinity and NaN as number literals (if this is
                         not present, they get turned into strings)
    """
    parser = argparse.ArgumentParser(description='Convert a PySON file to a JSON file')
    parser.add_argument('files', metavar='FILE', type=argparse.FileType(mode='rb'), nargs='+',
                        help='The files to convert')
    parser.add_argument('-quiet', action='store_true',
                        help="Don't print extra information while converting files")
    parser.add_argument('--stop-on-error', dest='stop_on_error', action='store_true',
                        help='Halt execution upon errors instead of skipping the file')
    parser.add_argument('--print-traceback', dest='print_traceback', action='store_true',
                        help='Print full traceback on error')
    parser.add_argument('--allow-inf-nan', dest='allow_inf_nan', action='store_true',
                        help='Allows Infinity and NaN as number literals (if this is not present, they get turned into strings)')

    try:
        args: argparse.Namespace = parser.parse_args(args)
    except FileNotFoundError as e:
        msg = str(e)
        i = msg.find('No such file or directory:')
        if i == -1:
            print('ERROR:', msg)
        else:
            file = msg[i+27:]
            print('ERROR: file not found:', file)
        exit(1)

    files: list = args.files
    verbose: bool = not args.quiet
    stop_on_error: bool = args.stop_on_error
    print_traceback: bool = args.print_traceback
    allow_inf_nan: bool = args.allow_inf_nan

    for file in files:
        filename: str = file.name
        with file:
            try:
                data = pyson.load(file, allow_inf_nan)
            except pyson.DataParseError as e:
                print(f"ERROR parsing file {path.basename(filename)!r}:\nPySON syntax error: {e}")
                if print_traceback:
                    import traceback
                    traceback.print_exc()
                if stop_on_error:
                    if verbose:
                        print('Stopped process early')
                    exit(1)
                else:
                    continue

        i = filename.rfind('.')
        if i == -1:
            newname = filename + '.json'
        else:
            newname = filename[:i] + '.json'

        def default(obj):
            if isinstance(obj, (bytes, bytearray)):
                return obj.decode('utf-8')
            elif isinstance(obj, (tuple, set)):
                return list(obj)
            else:
                return str(obj)

        keys = [key for key in data if isinstance(key, bytes)]

        for key in keys:
            data[key.decode('utf-8')] = data[key]
            del data[key]

        with open(newname, 'w') as file:
            json.dump(data, file, indent=4, default=default)

        if verbose:
            print("Converted", path.basename(newname))

if __name__ == "__main__":
    main()
    x = r"()(?x-x)\n"