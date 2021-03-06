import os
import calendar
import time
import sublime
from sublime_plugin import WindowCommand, TextCommand

from ..commands import *
from ...common import ui
from ..git_command import GitCommand
from ...common import util


class GsShowStatusCommand(WindowCommand, GitCommand):

    """
    Open a status view for the active git repository.
    """

    def run(self):
        StatusInterface(repo_path=self.repo_path)


class StatusInterface(ui.Interface, GitCommand):

    """
    Status dashboard.
    """

    interface_type = "status"
    read_only = True
    syntax_file = "Packages/GitSavvy/syntax/status.sublime-syntax"
    word_wrap = False
    tab_size = 2

    template = """\

      BRANCH:  {branch_status}
      ROOT:    {git_root}
      HEAD:    {head}

    {< unstaged_files}
    {< untracked_files}
    {< staged_files}
    {< merge_conflicts}
    {< no_status_message}
    {< stashes}
    {< help}
    """

    template_help = """
      ###################                   ###############
      ## SELECTED FILE ##                   ## ALL FILES ##
      ###################                   ###############

      [o] open file                         [a] stage all unstaged files
      [s] stage file                        [A] stage all unstaged and untracked files
      [u] unstage file                      [U] unstage all staged files
      [d] discard changes to file           [D] discard all unstaged changes
      [h] open file on remote
      [M] launch external merge tool

      [l] diff file inline                  [f] diff all files
      [e] diff file                         [F] diff all cached files

      #############                         #############
      ## ACTIONS ##                         ## STASHES ##
      #############                         #############

      [c] commit                            [t][a] apply stash
      [C] commit, including unstaged        [t][p] pop stash
      [m] amend previous commit             [t][s] show stash
      [p] push current branch               [t][c] create stash
                                            [t][u] create stash including untracked files
      [i] ignore file                       [t][g] create stash of staged changes only
      [I] ignore pattern                    [t][d] drop stash

      [B] abort merge

      ###########
      ## OTHER ##
      ###########

      [r]         refresh status
      [?]         toggle this help menu
      [tab]       transition to next dashboard
      [SHIFT-tab] transition to previous dashboard
      [.]         move cursor to next file
      [,]         move cursor to previous file
    {conflicts_bindings}
    -
    """

    conflicts_keybindings = """
    ###############
    ## CONFLICTS ##
    ###############

    [y] use version from your commit
    [b] use version from the base
    """

    template_staged = """
      STAGED:
    {}
    """

    template_unstaged = """
      UNSTAGED:
    {}
    """

    template_untracked = """
      UNTRACKED:
    {}
    """

    template_merge_conflicts = """
      MERGE CONFLICTS:
    {}
    """

    template_stashes = """
      STASHES:
    {}
    """

    def __init__(self, *args, **kwargs):
        self.conflicts_keybindings = \
            "\n".join(line[2:] for line in self.conflicts_keybindings.split("\n"))
        super().__init__(*args, **kwargs)

    def title(self):
        return "STATUS: {}".format(os.path.basename(self.repo_path))

    def pre_render(self):
        (self.staged_entries,
         self.unstaged_entries,
         self.untracked_entries,
         self.conflict_entries) = self.sort_status_entries(self.get_status())

    def on_new_dashboard(self):
        self.view.run_command("gs_status_navigate_file")

    def format_modification_time(self,ts):

        if self.savvy_settings.get("show_file_change_age") == None:
            return "   "
        if ts == 0:
            return "   "
        delta= calendar.timegm(time.gmtime())-ts
        if delta < 60:
            return "{0:2.0f}s".format(delta)
        delta/= 60
        if delta < 60:
            return "{0:2.0f}m".format(delta)
        delta/= 60
        if delta < 60:
            return "{0:2.0f}h".format(delta)
        delta/= 24
        if delta < 8:
            return "{0:2.0f}d".format(delta)
        delta/= 7
        if delta < 4:
            return "{0:2.0f}w".format(delta)
        delta/= 4
        if delta < 12:
            return "{0:2.0f}M".format(delta)
        delta/= 12
        return "{0:2.0f}Y".format(delta)

    @ui.partial("branch_status")
    def render_branch_status(self):
        return self.get_branch_status(delim="\n           ")

    @ui.partial("git_root")
    def render_git_root(self):
        return self.short_repo_path

    @ui.partial("head")
    def render_head(self):
        return self.get_latest_commit_msg_for_head()

    @ui.partial("staged_files")
    def render_staged_files(self):
        if not self.staged_entries:
            return ""

        def get_path(file_status):
            """ Display full file_status path, including path_alt if exists """
            if file_status.path_alt:
                return '{} -> {}'.format(file_status.path_alt, file_status.path)
            return file_status.path

        return self.template_staged.format("\n".join(
            "  {} {} {}".format(self.format_modification_time(f.modified), "-" if f.index_status == "D" else " ", get_path(f))
            for f in self.staged_entries
        ))

    @ui.partial("unstaged_files")
    def render_unstaged_files(self):
        if not self.unstaged_entries:
            return ""
        return self.template_unstaged.format("\n".join(
            "  {} {} {}".format(self.format_modification_time(f.modified), "-" if f.working_status == "D" else " ", f.path)
            for f in self.unstaged_entries
        ))

    @ui.partial("untracked_files")
    def render_untracked_files(self):
        if not self.untracked_entries:
            return ""
        return self.template_untracked.format("\n".join(
            "  {}   {}".format(self.format_modification_time(f.modified), f.path)
            for f in self.untracked_entries
        ))

    @ui.partial("merge_conflicts")
    def render_merge_conflicts(self):
        if not self.conflict_entries:
            return ""
        return self.template_merge_conflicts.format(
            "\n".join("    " + f.path for f in self.conflict_entries))

    @ui.partial("conflicts_bindings")
    def render_conflicts_bindings(self):
        return self.conflicts_keybindings if self.conflict_entries else ""

    @ui.partial("no_status_message")
    def render_no_status_message(self):
        return ("\n    Your working directory is clean.\n"
                if not (self.staged_entries or
                        self.unstaged_entries or
                        self.untracked_entries or
                        self.conflict_entries)
                else "")

    @ui.partial("stashes")
    def render_stashes(self):
        stash_list = self.get_stashes()
        if not stash_list:
            return ""

        return self.template_stashes.format("\n".join(
            "    ({}) {}".format(stash.id, stash.description) for stash in stash_list))

    @ui.partial("help")
    def render_help(self):
        help_hidden = self.view.settings().get("git_savvy.help_hidden")
        if help_hidden:
            return ""
        else:
            return self.template_help.format(
                conflicts_bindings=self.render_conflicts_bindings())


ui.register_listeners(StatusInterface)


class GsStatusOpenFileCommand(TextCommand, GitCommand):

    """
    For every file that is selected or under a cursor, open a that
    file in a new view.
    """

    def run(self, edit):
        lines = util.view.get_lines_from_regions(self.view, self.view.sel())
        file_paths = (line[7:].strip() for line in lines if line[5:8] == "   ")
        abs_paths = (os.path.join(self.repo_path, file_path) for file_path in file_paths)
        for path in abs_paths:
            self.view.window().open_file(path)


class GsStatusDiffInlineCommand(TextCommand, GitCommand):

    """
    For every file selected or under a cursor, open a new inline-diff view for
    that file.  If the file is staged, open the inline-diff in cached mode.
    """

    def run(self, edit):
        interface = ui.get_interface(self.view.id())

        non_cached_sections = (interface.get_view_regions("unstaged_files") +
                               interface.get_view_regions("merge_conflicts"))
        non_cached_lines = util.view.get_lines_from_regions(
            self.view,
            self.view.sel(),
            valid_ranges=non_cached_sections
        )
        non_cached_files = (
            os.path.join(self.repo_path, line[7:].strip())
            for line in non_cached_lines
            if line[5:8] == "   ")

        cached_sections = interface.get_view_regions("staged_files")
        cached_lines = util.view.get_lines_from_regions(
            self.view,
            self.view.sel(),
            valid_ranges=cached_sections
        )
        cached_files = (
            os.path.join(self.repo_path, line[7:].strip())
            for line in cached_lines
            if line[5:8] == "   ")

        sublime.set_timeout_async(
            lambda: self.load_inline_diff_windows(non_cached_files, cached_files), 0)

    def load_inline_diff_windows(self, non_cached_files, cached_files):
        for fpath in non_cached_files:
            syntax = util.file.get_syntax_for_file(fpath)
            settings = {
                "git_savvy.file_path": fpath,
                "git_savvy.repo_path": self.repo_path,
                "syntax": syntax
            }
            self.view.window().run_command("gs_inline_diff", {"settings": settings})

        for fpath in cached_files:
            syntax = util.file.get_syntax_for_file(fpath)
            settings = {
                "git_savvy.file_path": fpath,
                "git_savvy.repo_path": self.repo_path,
                "syntax": syntax
            }
            self.view.window().run_command("gs_inline_diff", {
                "settings": settings,
                "cached": True
            })


class GsStatusDiffCommand(TextCommand, GitCommand):

    """
    For every file selected or under a cursor, open a new diff view for
    that file.  If the file is staged, open the diff in cached mode.
    """

    def run(self, edit):
        interface = ui.get_interface(self.view.id())

        non_cached_sections = (interface.get_view_regions("unstaged_files") +
                               interface.get_view_regions("untracked_files") +
                               interface.get_view_regions("merge_conflicts"))
        non_cached_lines = util.view.get_lines_from_regions(
            self.view,
            self.view.sel(),
            valid_ranges=non_cached_sections
        )
        non_cached_files = (
            os.path.join(self.repo_path, line[7:].strip())
            for line in non_cached_lines
            if line[5:8] == "   "
        )

        cached_sections = interface.get_view_regions("staged_files")
        cached_lines = util.view.get_lines_from_regions(
            self.view,
            self.view.sel(),
            valid_ranges=cached_sections
        )
        cached_files = (
            os.path.join(self.repo_path, line[7:].strip())
            for line in cached_lines
            if line[5:8] == "   "
        )

        sublime.set_timeout_async(
            lambda: self.load_diff_windows(non_cached_files, cached_files), 0)

    def load_diff_windows(self, non_cached_files, cached_files):
        for fpath in non_cached_files:
            self.view.window().run_command("gs_diff", {
                "file_path": fpath,
                "current_file": True
            })

        for fpath in cached_files:
            self.view.window().run_command("gs_diff", {
                "file_path": fpath,
                "in_cached_mode": True,
                "current_file": True
            })


class GsStatusStageFileCommand(TextCommand, GitCommand):

    """
    For every file that is selected or under a cursor, if that file is
    unstaged, stage it.
    """

    def run(self, edit):
        interface = ui.get_interface(self.view.id())
        valid_ranges = (interface.get_view_regions("unstaged_files") +
                        interface.get_view_regions("untracked_files") +
                        interface.get_view_regions("merge_conflicts"))

        lines = util.view.get_lines_from_regions(
            self.view,
            self.view.sel(),
            valid_ranges=valid_ranges
        )
        # Remove the leading spaces and hyphen-character for deleted files.
        file_paths = tuple(line[7:].strip() for line in lines if line)

        if file_paths:
            for fpath in file_paths:
                self.stage_file(fpath, force=False)
            self.view.window().status_message("Staged files successfully.")
            util.view.refresh_gitsavvy(self.view)


class GsStatusUnstageFileCommand(TextCommand, GitCommand):

    """
    For every file that is selected or under a cursor, if that file is
    staged, unstage it.
    """

    def run(self, edit):
        interface = ui.get_interface(self.view.id())
        valid_ranges = interface.get_view_regions("staged_files")
        lines = util.view.get_lines_from_regions(
            self.view,
            self.view.sel(),
            valid_ranges=valid_ranges
        )
        # Remove the leading spaces and hyphen-character for deleted files.
        file_paths = tuple(line[7:].strip() for line in lines if line)

        if file_paths:
            for fpath in file_paths:
                self.unstage_file(fpath)
            self.view.window().status_message("Unstaged files successfully.")
            util.view.refresh_gitsavvy(self.view)


class GsStatusDiscardChangesToFileCommand(TextCommand, GitCommand):

    """
    For every file that is selected or under a cursor, if that file is
    unstaged, reset the file to HEAD.  If it is untracked, delete it.
    """

    def run(self, edit):
        interface = ui.get_interface(self.view.id())
        self.discard_untracked(interface)
        self.discard_unstaged(interface)
        util.view.refresh_gitsavvy(self.view)
        self.view.window().status_message("Successfully discarded changes.")

    def discard_untracked(self, interface):
        valid_ranges = interface.get_view_regions("untracked_files")
        lines = util.view.get_lines_from_regions(
            self.view,
            self.view.sel(),
            valid_ranges=valid_ranges
        )
        file_paths = tuple(line[7:].strip() for line in lines if line)

        @util.actions.destructive(description="discard one or more untracked files")
        def do_discard():
            for fpath in file_paths:
                self.discard_untracked_file(fpath)

        if file_paths:
            do_discard()

    def discard_unstaged(self, interface):
        valid_ranges = (interface.get_view_regions("unstaged_files") +
                        interface.get_view_regions("merge_conflicts"))
        lines = util.view.get_lines_from_regions(
            self.view,
            self.view.sel(),
            valid_ranges=valid_ranges
        )
        file_paths = tuple(line[7:].strip() for line in lines if line)

        @util.actions.destructive(description="discard one or more unstaged files")
        def do_discard():
            for fpath in file_paths:
                self.checkout_file(fpath)

        if file_paths:
            do_discard()


class GsStatusOpenFileOnRemoteCommand(TextCommand, GitCommand):

    """
    For every file that is selected or under a cursor, open a new browser
    window to that file on GitHub.
    """

    def run(self, edit):
        interface = ui.get_interface(self.view.id())
        valid_ranges = (interface.get_view_regions("unstaged_files") +
                        interface.get_view_regions("merge_conflicts") +
                        interface.get_view_regions("staged_files"))

        lines = util.view.get_lines_from_regions(
            self.view,
            self.view.sel(),
            valid_ranges=valid_ranges
        )
        file_paths = tuple(line[7:].strip() for line in lines if line)
        self.view.run_command("gs_open_file_on_remote", {"fpath": list(file_paths)})


class GsStatusStageAllFilesCommand(TextCommand, GitCommand):

    """
    Stage all unstaged files.
    """

    def run(self, edit):
        self.add_all_tracked_files()
        util.view.refresh_gitsavvy(self.view)


class GsStatusStageAllFilesWithUntrackedCommand(TextCommand, GitCommand):

    """
    Stage all unstaged files, including new files.
    """

    def run(self, edit):
        self.add_all_files()
        util.view.refresh_gitsavvy(self.view)


class GsStatusUnstageAllFilesCommand(TextCommand, GitCommand):

    """
    Unstage all staged changes.
    """

    def run(self, edit):
        self.unstage_all_files()
        util.view.refresh_gitsavvy(self.view)


class GsStatusDiscardAllChangesCommand(TextCommand, GitCommand):

    """
    Reset all unstaged files to HEAD.
    """

    @util.actions.destructive(description="discard all unstaged changes, "
                                          "and delete all untracked files")
    def run(self, edit):
        self.discard_all_unstaged()
        util.view.refresh_gitsavvy(self.view)


class GsStatusCommitCommand(TextCommand, GitCommand):

    """
    Open a commit window.
    """

    def run(self, edit):
        self.view.window().run_command("gs_commit", {"repo_path": self.repo_path})


class GsStatusCommitUnstagedCommand(TextCommand, GitCommand):

    """
    Open a commit window.  When the commit message is provided, stage all unstaged
    changes and then do the commit.
    """

    def run(self, edit):
        self.view.window().run_command(
            "gs_commit",
            {"repo_path": self.repo_path, "include_unstaged": True}
        )


class GsStatusAmendCommand(TextCommand, GitCommand):

    """
    Open a commit window to amend the previous commit.
    """

    def run(self, edit):
        self.view.window().run_command(
            "gs_commit",
            {"repo_path": self.repo_path, "amend": True}
        )


class GsStatusIgnoreFileCommand(TextCommand, GitCommand):

    """
    For each file that is selected or under a cursor, add an
    entry to the git root's `.gitignore` file.
    """

    def run(self, edit):
        interface = ui.get_interface(self.view.id())
        valid_ranges = (interface.get_view_regions("unstaged_files") +
                        interface.get_view_regions("untracked_files") +
                        interface.get_view_regions("merge_conflicts") +
                        interface.get_view_regions("staged_files"))
        lines = util.view.get_lines_from_regions(
            self.view,
            self.view.sel(),
            valid_ranges=valid_ranges
        )
        file_paths = tuple(line[7:].strip() for line in lines if line)

        if file_paths:
            for fpath in file_paths:
                self.add_ignore(os.path.join("/", fpath))
            self.view.window().status_message("Successfully ignored files.")
            util.view.refresh_gitsavvy(self.view)


class GsStatusIgnorePatternCommand(TextCommand, GitCommand):

    """
    For the first file that is selected or under a cursor (other
    selections/cursors will be ignored), prompt the user for
    a new pattern to `.gitignore`, prefilled with the filename.
    """

    def run(self, edit):
        interface = ui.get_interface(self.view.id())
        valid_ranges = (interface.get_view_regions("unstaged_files") +
                        interface.get_view_regions("untracked_files") +
                        interface.get_view_regions("merge_conflicts") +
                        interface.get_view_regions("staged_files"))
        lines = util.view.get_lines_from_regions(
            self.view,
            self.view.sel(),
            valid_ranges=valid_ranges
        )
        file_paths = tuple(line[7:].strip() for line in lines if line)

        if file_paths:
            self.view.window().run_command("gs_ignore_pattern", {"pre_filled": file_paths[0]})


class GsStatusStashCommand(TextCommand, GitCommand):

    """
    Run action from status dashboard to stash commands. Need to have this command to
    read the interface and call the stash commands

    action          multipul staches
    show            True
    apply           False
    pop             False
    discard         False
    """

    def run(self, edit, action=None):
        interface = ui.get_interface(self.view.id())
        lines = util.view.get_lines_from_regions(
            self.view,
            self.view.sel(),
            valid_ranges=interface.get_view_regions("stashes")
        )
        ids = tuple(line[line.find("(") + 1:line.find(")")] for line in lines if line)

        if len(ids) == 0:
            # happens if command get called when none of the cursors
            # is pointed on one stash
            return

        if action == "show":
            self.view.window().run_command("gs_stash_show", {"stash_ids": ids})
            return

        if len(ids) > 1:
            self.view.window().status_message("You can only {} one stash at a time.".format(action))
            return

        if action == "apply":
            self.view.window().run_command("gs_stash_apply", {"stash_id": ids[0]})
        elif action == "pop":
            self.view.window().run_command("gs_stash_pop", {"stash_id": ids[0]})
        elif action == "drop":
            self.view.window().run_command("gs_stash_drop", {"stash_id": ids[0]})


class GsStatusLaunchMergeToolCommand(TextCommand, GitCommand):

    """
    Launch external merge tool for selected file.
    """

    def run(self, edit):
        interface = ui.get_interface(self.view.id())
        valid_ranges = (interface.get_view_regions("unstaged_files") +
                        interface.get_view_regions("untracked_files") +
                        interface.get_view_regions("merge_conflicts") +
                        interface.get_view_regions("staged_files"))
        lines = util.view.get_lines_from_regions(
            self.view,
            self.view.sel(),
            valid_ranges=valid_ranges
        )
        file_paths = tuple(line[7:].strip() for line in lines if line)

        if len(file_paths) > 1:
            sublime.error_message("You can only launch merge tool for a single file at a time.")
            return

        sublime.set_timeout_async(lambda: self.launch_tool_for_file(file_paths[0]), 0)


class GsStatusUseCommitVersionCommand(TextCommand, GitCommand):
    # TODO: refactor this alongside interfaces.rebase.GsRebaseUseCommitVersionCommand

    def run(self, edit):
        sublime.set_timeout_async(self.run_async, 0)

    def run_async(self):
        interface = ui.get_interface(self.view.id())
        conflicts = interface.conflict_entries

        sels = self.view.sel()
        line_regions = [self.view.line(sel) for sel in sels]
        paths = (line[5:]
                 for reg in line_regions
                 for line in self.view.substr(reg).split("\n") if line)
        for path in paths:
            if self.is_commit_version_deleted(path, conflicts):
                self.git("rm", "--", path)
            else:
                self.git("checkout", "--theirs", "--", path)
                self.stage_file(path)
        util.view.refresh_gitsavvy(self.view)

    def is_commit_version_deleted(self, path, conflicts):
        for conflict in conflicts:
            if conflict.path == path:
                return conflict.working_status == "D"
        return False


class GsStatusUseBaseVersionCommand(TextCommand, GitCommand):

    def run(self, edit):
        sublime.set_timeout_async(self.run_async, 0)

    def run_async(self):
        interface = ui.get_interface(self.view.id())
        conflicts = interface.conflict_entries

        sels = self.view.sel()
        line_regions = [self.view.line(sel) for sel in sels]
        paths = (line[5:]
                 for reg in line_regions
                 for line in self.view.substr(reg).split("\n") if line)
        for path in paths:
            if self.is_base_version_deleted(path, conflicts):
                self.git("rm", "--", path)
            else:
                self.git("checkout", "--ours", "--", path)
                self.stage_file(path)
        util.view.refresh_gitsavvy(self.view)

    def is_base_version_deleted(self, path, conflicts):
        for conflict in conflicts:
            if conflict.path == path:
                return conflict.index_status == "D"
        return False


class GsStatusNavigateFileCommand(GsNavigate):

    """
    Move cursor to the next (or previous) selectable file in the dashboard.
    """

    def get_available_regions(self):
        file_regions = [file_region
                        for region in self.view.find_by_selector("meta.git-savvy.status.file")
                        for file_region in self.view.lines(region)]

        stash_regions = [stash_region
                         for region in self.view.find_by_selector("meta.git-savvy.status.saved_stash")
                         for stash_region in self.view.lines(region)]

        return file_regions + stash_regions
