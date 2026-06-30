# Dotfiles

Personal macOS dotfiles for `rianrainey`. This repo is meant to be easy to use on a new computer and easy for an agent to operate without guessing.

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

This repo should use the personal GitHub account `rianrainey`, not a work account.

Expected SSH aliases:

```sshconfig
Host github.com-rianrainey
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_github_rianrainey
  IdentitiesOnly yes

Host github.com github.com-goodrx
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_rsa
  IdentitiesOnly yes
```

Verify personal GitHub auth:

```sh
ssh -T git@github.com-rianrainey
```

Expected result includes:

```text
Hi rianrainey! You've successfully authenticated
```

### 3. Clone the repo

```sh
mkdir -p ~/Documents/code
git clone git@github.com-rianrainey:rianrainey/dotfiles.git ~/Documents/code/dotfiles
cd ~/Documents/code/dotfiles
```

Set repo-local Git identity:

```sh
git config user.name "Rian Rainey"
git config user.email "rianrainey@gmail.com"
git remote set-url origin git@github.com-rianrainey:rianrainey/dotfiles.git
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
```

If the dry run looks right, run without `-n`:

```sh
stow -v -t "$HOME" zshrc
stow -v -t "$HOME" tmux
stow -v -t "$HOME" git
stow -v -t "$HOME" ghostty
stow -v -t "$HOME" tmux-sessionizer
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
| `nvim` | `~/.config/nvim` | Neovim config |

## Reload Commands

Reload zsh:

```sh
source ~/.zshrc
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
- This repo should commit as `Rian Rainey <rianrainey@gmail.com>`.
- This repo should push through `git@github.com-rianrainey:rianrainey/dotfiles.git`.
- Work GitHub repos should use the `github.com-goodrx` SSH alias or plain `github.com`.
