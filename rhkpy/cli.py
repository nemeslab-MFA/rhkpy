"""Command line interface: inspect and picture .sm4 files without writing Python.

Run ``rhkpy --help``, or ``python -m rhkpy --help``. Results go to stdout, and
everything else (warnings, the reader's messages) to stderr, so that the output
of ``--json`` can always be parsed.
"""

import argparse
import contextlib
import json
import os
import sys

from .core import rhkdata
from .guide import agent_guide
from .summary import scan
from .version import __version__


def _summary_text(summary):
	"""The main facts of a summary, for reading in a terminal."""
	kind = summary['datatype'] if summary['spectype'] is None else f'{summary["datatype"]}, {summary["spectype"]}'
	lines = [
		f'file: {summary["filename"]}',
		f'type: {kind}',
		f'measured: {summary["measurement_date"]} {summary["measurement_time"]}',
		f'bias: {summary["bias_V"]} V, setpoint: {summary["setpoint_pA"]} pA',
	]
	image = summary['image']
	if image is not None:
		lines.append(f'image: {image["pixels"]["x"]} x {image["pixels"]["y"]} pixels, {image["size_nm"]["x"]} x {image["size_nm"]["y"]} nm')
	spectra = summary['spectra']
	if spectra is not None:
		sweep = spectra['sweep']
		lines.append('spectra: ' + ', '.join(f'{dim} {size}' for dim, size in spectra['sizes'].items()))
		lines.append(f'sweep: {sweep["name"]} {sweep["start"]} to {sweep["stop"]} {sweep["units"]}, {sweep["points"]} points')
	lines += [f'note: {note}' for note in summary['notes']]
	return '\n'.join(lines)


def _scan_line(summary):
	"""One line of a folder listing."""
	if 'error' in summary:
		return f'{summary["path"]}: {summary["error"]}'
	kind = summary['datatype'] if summary['spectype'] is None else f'{summary["datatype"]}, {summary["spectype"]}'
	spectra = summary['spectra']
	sizes = '' if spectra is None else ' ' + ', '.join(f'{dim} {size}' for dim, size in spectra['sizes'].items())
	return f'{summary["path"]}: {kind}{sizes}'


def _info(args):
	summary = rhkdata(args.file).summary()
	return json.dumps(summary, indent = 1) if args.json else _summary_text(summary)


def _scan(args):
	summaries = scan(args.folder, recursive = args.recursive)
	if args.json:
		return json.dumps(summaries, indent = 1)
	return '\n'.join(_scan_line(summary) for summary in summaries)


def _preview(args):
	output = args.output or os.path.splitext(os.path.basename(args.file))[0] + '.png'
	rhkdata(args.file).preview(output, dpi = args.dpi, at = args.at)
	return output


def _guide(args):
	return agent_guide()


def _parser():
	parser = argparse.ArgumentParser(prog = 'rhkpy', description = 'Inspect and picture RHK .sm4 STM measurements.')
	parser.add_argument('--version', action = 'version', version = f'rhkpy {__version__}')
	commands = parser.add_subparsers(dest = 'command', required = True)

	info = commands.add_parser('info', help = 'describe one file')
	info.add_argument('file')
	info.add_argument('--json', action = 'store_true', help = 'print the full summary as JSON')
	info.set_defaults(run = _info)

	scan_command = commands.add_parser('scan', help = 'describe every .sm4 file in a folder; files that fail are reported, not fatal')
	scan_command.add_argument('folder')
	scan_command.add_argument('--recursive', action = 'store_true', help = 'also look in subfolders')
	scan_command.add_argument('--json', action = 'store_true', help = 'print the full summaries as JSON')
	scan_command.set_defaults(run = _scan)

	preview = commands.add_parser('preview', help = 'save a picture of one file and print its path; needs no browser')
	preview.add_argument('file')
	preview.add_argument('-o', '--output', help = 'output file, defaults to the name of the input with .png, in the current folder')
	preview.add_argument('--at', type = float, help = 'for maps, the sweep value to show: bias in V or z in nm; defaults to the middle of the sweep')
	preview.add_argument('--dpi', type = int, default = 150, help = 'resolution, defaults to 150')
	preview.set_defaults(run = _preview)

	guide = commands.add_parser('guide', help = 'print the guide to using rhkpy from scripts and AI agents')
	guide.set_defaults(run = _guide)
	return parser


def main(argv = None):
	"""Run a command and return the process exit code."""
	args = _parser().parse_args(argv)
	result = sys.stdout
	try:
		# the reader prints its errors, which must not end up in the results
		with contextlib.redirect_stdout(sys.stderr):
			output = args.run(args)
	except Exception as exc:
		print(f'rhkpy: {type(exc).__name__}: {exc}', file = sys.stderr)
		return 1
	print(output, file = result)
	return 0
