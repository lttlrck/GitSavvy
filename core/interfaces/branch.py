import os
from itertools import groupby

from ...common import ui
from ..git_command import GitCommand

from sublime_plugin import WindowCommand, TextCommand


interfaces = {}


class GsShowBranchCommand(WindowCommand, GitCommand):

    """
    Open a branch dashboard for the active Git repository.
    """

    def run(self):
        BranchInterface(view_attrs={"git_savvy.repo_path": self.repo_path})


class BranchInterface(ui.Interface, GitCommand):

    """
    """

    interface_type = "branch"
    read_only = True
    view_type = "branches"
    syntax_file = "Packages/GitSavvy/syntax/branch.tmLanguage"
    word_wrap = False

    dedent = 4
    skip_first_line = True

    template = """

      BRANCH:  {branch_status}
      ROOT:    {git_root}
      HEAD:    {head}

      LOCAL:
    {branch_list}{remotes}
      #############
      ## ACTIONS ##
      #############

      [c] checkout                                  [p] push selected to remote
      [b] create new branch (from selected)         [P] push all branches to remote
      [d] delete
      [r] rename                                    [m] merge selected into active branch
      [t] configure tracking                        [M] fetch and merge into active branch

      [f] diff against active
      [r] refresh

    -
    """

    template_remote = """
      REMOTE ({remote_name}):
    {remote_branch_list}"""

    def title(self):
        return "BRANCHES: {}".format(os.path.basename(self.repo_path))

    def pre_render(self):
        self._branches = tuple(self.get_branches())

    @ui.partial("branch_status")
    def render_branch_status(self):
        return self.get_branch_status()

    @ui.partial("git_root")
    def render_git_root(self):
        return self.repo_path

    @ui.partial("head")
    def render_head(self):
        return self.get_latest_commit_msg_for_head()

    @ui.partial("branch_list")
    def render_branch_list(self, branches=None):
        if not branches:
            branches = [branch for branch in self._branches if not branch.remote]

        return "\n".join(
            "  {indicator} {hash:.7} {name} {tracking}".format(
                indicator="▸" if branch.active else " ",
                hash=branch.commit_hash,
                name=branch.name,
                tracking=("({branch}{status})".format(
                    branch=branch.tracking,
                    status=", " + branch.tracking_status if branch.tracking_status else ""
                    )
                    if branch.tracking else "")
                )
            for branch in branches
            )

    @ui.partial("remotes")
    def render_remotes(self):
        output_tmpl = "\n"
        render_fns = []

        for remote_name, branches in groupby(self._branches, lambda branch: branch.remote):
            if not remote_name:
                continue

            branches = tuple(branches)
            key = "branch_list_" + remote_name
            output_tmpl += "{" + key + "}\n"

            @ui.partial(key)
            def render(remote_name=remote_name, branches=branches):
                return self.template_remote.format(
                    remote_name=remote_name,
                    remote_branch_list=self.render_branch_list(branches=branches)
                    )

            render_fns.append(render)

        return output_tmpl, render_fns


ui.register_listeners(BranchInterface)


class GsBranchesCheckoutCommand(TextCommand, GitCommand):

    """
    Checkout the selected branch.
    """

    def run(self, edit):
        pass


class GsBranchesCreateNewCommand(TextCommand, GitCommand):

    """
    Create a new branch from selected branch and checkout.
    """

    def run(self, edit):
        pass


class GsBranchesDeleteCommand(TextCommand, GitCommand):

    """
    Delete selected branch.
    """

    def run(self, edit):
        pass


class GsBranchesRenameCommand(TextCommand, GitCommand):

    """
    Rename selected branch.
    """

    def run(self, edit):
        pass


class GsBranchesConfigureTrackingCommand(TextCommand, GitCommand):

    """
    Configure remote branch to track against for selected branch.
    """

    def run(self, edit):
        pass


class GsBranchesPushSelectedCommand(TextCommand, GitCommand):

    """
    Push selected branch to remote.
    """

    def run(self, edit):
        pass


class GsBranchesPushAllCommand(TextCommand, GitCommand):

    """
    Push all branches to remote.
    """

    def run(self, edit):
        pass


class GsBranchesMergeSelectedCommand(TextCommand, GitCommand):

    """
    Merge selected branch into active branch.
    """

    def run(self, edit):
        pass


class GsBranchesFetchAndMergeCommand(TextCommand, GitCommand):

    """
    Fetch from remote and merge fetched branch into active branch.
    """

    def run(self, edit):
        pass


class GsBranchesDiffBranchCommand(TextCommand, GitCommand):

    """
    Show a diff comparing the selected branch to the active branch.
    """

    def run(self, edit):
        pass


class GsBranchesRefreshCommand(TextCommand, GitCommand):

    """
    Refresh the branch dashboard.
    """

    def run(self, edit):
        pass
