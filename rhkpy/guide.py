"""Access to the guide shipped inside the package."""

from importlib import resources


def agent_guide():
	"""The guide to using rhkpy from scripts and AI agents: the data model, how to inspect and
	picture measurements without a notebook, errors and pitfalls. Also printed by ``rhkpy guide``.

	:return: the guide, as markdown text
	:rtype: str
	"""
	return resources.files('rhkpy').joinpath('AGENT_GUIDE.md').read_text(encoding = 'utf-8')
