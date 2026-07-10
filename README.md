# Dotfiles

Personal macOS dotfiles. This repo is meant to be easy to use on a new computer and easy for an agent to operate without guessing.

The repo uses [GNU Stow](https://www.gnu.org/software/stow/) packages. Each top-level directory is a package whose contents should be symlinked into `$HOME`.

## New Computer Setup

### 1. Install basics

```sh
xcode-select --install
brew install git stow tmux fzf
```

Install app-specific tools as needed:

```sh
brew install --cask ghostty
brew install neovim
```

### 2. Configure personal GitHub SSH

This repo should use a personal GitHub account, not a work account.

Before editing SSH or Git config, fill in these placeholders:

| Placeholder | Meaning |
| --- | --- |
| `<personal-github-user>` | Personal GitHub username |
| `<developer-name>` | Git author name |
| `<personal-email>` | Personal Git author email |
| `<work-github-label>` | Short label for the work account or company |
| `<personal-ssh-key>` | Personal SSH private key filename |
| `<work-ssh-key>` | Work SSH private key filename |

Expected SSH aliases:

```sshconfig
Host github.com-personal
  HostName github.com
  User git
  IdentityFile ~/.ssh/<personal-ssh-key>
  IdentitiesOnly yes

Host github.com github.com-<work-github-label>
  HostName github.com
  User git
  IdentityFile ~/.ssh/<work-ssh-key>
  IdentitiesOnly yes
```

Verify personal GitHub auth:

```sh
ssh -T git@github.com-personal
```

Expected result includes:

```text
Hi <personal-github-user>! You've successfully authenticated
```

### 3. Clone the repo

```sh
mkdir -p ~/Documents/code
git clone git@github.com-personal:<personal-github-user>/dotfiles.git ~/Documents/code/dotfiles
cd ~/Documents/code/dotfiles
```

Set repo-local Git identity:

```sh
git config user.name "<developer-name>"
git config user.email "<personal-email>"
git remote set-url origin git@github.com-personal:<personal-github-user>/dotfiles.git
```

Verify:

```sh
git config user.email
git remote -v
```

### 4. Stow packages

Always dry-run first:

```sh
stow -n -v -t "$HOME" zshrc
stow -n -v -t "$HOME" tmux
stow -n -v -t "$HOME" git
stow -n -v -t "$HOME" ghostty
stow -n -v -t "$HOME" tmux-sessionizer
stow -n -v -t "$HOME" aerospace
stow -n -v -t "$HOME" agents
```

If the dry run looks right, run without `-n`:

```sh
stow -v -t "$HOME" zshrc
stow -v -t "$HOME" tmux
stow -v -t "$HOME" git
stow -v -t "$HOME" ghostty
stow -v -t "$HOME" tmux-sessionizer
stow -v -t "$HOME" aerospace
stow -v -t "$HOME" agents
```

For Neovim, target `~/.config/nvim`:

```sh
mkdir -p ~/.config/nvim
stow -n -v -t ~/.config/nvim nvim
stow -v -t ~/.config/nvim nvim
```

If Stow reports a conflict, move the existing file out of the way first:

```sh
mv ~/.zshrc ~/.zshrc.backup
stow -v -t "$HOME" zshrc
```

## Package Map

| Package | Links into | Purpose |
| --- | --- | --- |
| `zshrc` | `~/.zshrc` | Shell startup config |
| `tmux` | `~/.tmux.conf` | Tmux prefix, key bindings, status line |
| `git` | `~/.gitconfig` | Git defaults |
| `ghostty` | `~/.config/ghostty/config` | Ghostty terminal config |
| `tmux-sessionizer` | `~/.config/tmux-sessionizer`, `~/.local/bin` | Project/session picker |
| `aerospace` | `~/.aerospace.toml` | AeroSpace workspace, monitor, and app routing |
| `nvim` | `~/.config/nvim` | Neovim config |
| `agents` | `~/.codex/skills` | Personal Codex skills, excluding bundled system skills |

## Codex Skills

Personal Codex skills live in `agents/.codex/skills` so they can be version controlled with the rest of these dotfiles. Codex-bundled `.system` skills are intentionally excluded because Codex provides them itself.

Preview the links before installing:

```sh
stow -n -v -t "$HOME" agents
```

Install them:

```sh
stow -v -t "$HOME" agents
```

On a machine that already has real files in `~/.codex/skills`, the dry run will report conflicts. Keep the versioned copy as the source of truth and convert those files to symlinks only after reviewing that migration separately.

## Reload Commands

Reload zsh:

```sh
source ~/.zshrc
```

## Zsh Directory Finder

The `zshrc` package enables the existing Oh My Zsh `fzf` plugin. It provides fuzzy directory navigation without custom shell functions.

From any directory:

```text
Alt-c
```

opens a fuzzy finder for child directories and `cd`s into the selected directory. This is useful from `~/Documents/code` when you remember a ticket prefix but not the exact worktree path.

You can also fuzzy-complete directories:

```sh
cd **<Tab>
```

Reload tmux:

```sh
tmux source-file ~/.tmux.conf
```

If tmux theme/status settings look stale, restart the tmux server:

```sh
tmux kill-server
tmux
```

## Tmux Notes

Current prefix:

```text
Ctrl-d
```

Useful bindings:

```text
Ctrl-d r  reload ~/.tmux.conf
Ctrl-d S  create or switch to a named session
Ctrl-d f  open tmux-sessionizer
```

Install tmux plugins with TPM:

```text
Ctrl-d I
```

TPM lives at:

```text
~/.tmux/plugins/tpm
```

Install it if missing:

```sh
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
```

## Agent Notes

- Treat each top-level directory as a separate Stow package.
- Keep commits split by package or concern.
- Do not commit machine-local secrets, tokens, `.env` files, or SSH private keys.
- Use `stow -n -v -t "$HOME" <package>` before changing symlinks.
- Prompt for `<developer-name>`, `<personal-email>`, `<personal-github-user>`, and SSH key filenames before writing Git or SSH config.
- This repo should commit as `<developer-name> <<personal-email>>`.
- This repo should push through `git@github.com-personal:<personal-github-user>/dotfiles.git`.
- Work GitHub repos should use the `github.com-<work-github-label>` SSH alias or plain `github.com`.
