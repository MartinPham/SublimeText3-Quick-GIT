import os
import sublime
import sublime_plugin
import threading
import subprocess
import functools
import os.path
import time


def main_thread(callback, *args, **kwargs):
    # sublime.set_timeout gets used to send things onto the main thread
    # most sublime.[something] calls need to be on the main thread
    sublime.set_timeout(functools.partial(callback, *args, **kwargs), 0)

def _make_text_safeish(text, fallback_encoding, method='decode'):
    # The unicode decode here is because sublime converts to unicode inside
    # insert in such a way that unknown characters will cause errors, which is
    # distinctly non-ideal... and there's no way to tell what's coming out of
    # git in output. So...
    # try:
    #     unitext = getattr(text, method)('utf-8')
    # except (UnicodeEncodeError, UnicodeDecodeError):
    #     unitext = getattr(text, method)(fallback_encoding)
    return text

class ZpCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.working_dir = os.path.realpath(os.path.dirname(self.view.file_name()))

		print("Pulling...")

		self.run_command(['git', 'pull', 'origin', 'master'], self.pulled, working_dir = self.working_dir)
	def pulled(self, text):
		print("Pulled")	
		# sublime.active_window().run_command("show_panel", {"panel": "console", "toggle": True})

	def run_command(self, command, callback=None, show_status=True, filter_empty_args=True, no_save=False, **kwargs):
		thread = CommandThread(command, callback, **kwargs)
		thread.start()

class ZacpCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.working_dir = os.path.realpath(os.path.dirname(self.view.file_name()))

		sublime.active_window().show_input_panel("Commit message:", "ok", self.inputted, None, None)

		

	def run_command(self, command, callback=None, show_status=True, filter_empty_args=True, no_save=False, **kwargs):
		thread = CommandThread(command, callback, **kwargs)
		thread.start()

	def inputted(self, text):
		self.commit_message = text
		
		sublime.active_window().run_command("show_panel", {"panel": "console", "toggle": True})

		self.view.run_command('save')

		print("Adding...")

		self.run_command(['git', 'add', '--all', ':/'], self.added, working_dir = self.working_dir)

	def added(self, result):
		print("Added")

		print("Committing...")

		self.run_command(['git', 'commit', '-m', self.commit_message], self.committed, working_dir = self.working_dir)
	def committed(self, result):
		print("Committed")

		print("Pushing...")

		self.run_command(['git', 'push', 'origin', 'master'], self.pushed, working_dir = self.working_dir)
	def pushed(self, result):
		print("Pushed")	
		# sublime.active_window().run_command("show_panel", {"panel": "console", "toggle": True})

class CommandThread(threading.Thread):
	def __init__(self, command, on_done, working_dir="", fallback_encoding="", **kwargs):
		threading.Thread.__init__(self)
		self.command = command
		self.on_done = on_done
		self.working_dir = working_dir
		if "stdin" in kwargs:
			self.stdin = kwargs["stdin"]
		else:
			self.stdin = None
		if "stdout" in kwargs:
			self.stdout = kwargs["stdout"]
		else:
			self.stdout = subprocess.PIPE
		self.fallback_encoding = fallback_encoding
		self.kwargs = kwargs

	def run(self):

			# Ignore directories that no longer exist
			if os.path.isdir(self.working_dir):

				# Per http://bugs.python.org/issue8557 shell=True is required to
				# get $PATH on Windows. Yay portable code.
				shell = os.name == 'nt'
				if self.working_dir != "":
					os.chdir(self.working_dir)

				proc = subprocess.Popen(self.command,
					stdout=self.stdout, stderr=subprocess.STDOUT,
					stdin=subprocess.PIPE,
					shell=shell, universal_newlines=True,
					env=os.environ)
				output = proc.communicate(self.stdin)[0]

				print(output)

				if not output:
					output = ''
				# if sublime's python gets bumped to 2.7 we can just do:
				# output = subprocess.check_output(self.command)
				main_thread(self.on_done, _make_text_safeish(output, self.fallback_encoding), **self.kwargs)