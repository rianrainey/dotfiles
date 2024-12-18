# Dotfiles

This uses [Stow](https://www.gnu.org/software/stow/) to symlink my dotfiles

## Guidance

Put application dotfiles in respective folder. For example, `~/dotfiles/vim/.vimrc` would have all the symlinked dotfiles for `~/.vimrc` on my machine. Stow symlinks up 1 directory, fyi. You might be able to use target directories to get around that design.


## Usage

```
cd ~
git clone git@github.com:rianrainey/dotfiles.git
stow git # Or whatever module you what to symlink

### How to add new dotfiles
```
cd ~/dotfiles
mv ~/.config/nvim ./nvim # Move current config to dotfiles
mkdir ~/.config/nvim # Create directory first
stow -t ~/.config/nvim nvim # Target specific directory instead of just parent directory

### How to source tmux

### How to source vimrc
`source $MYVIMRC`
or
`<leader>vr # as found in init.lua`

```
## Steps For New Install

```
sh osx-settings-configure.sh
sh setup.sh
```

## Other Steps

1. [Get iTerm Color Schemes](http://iterm2colorschemes.com/)
