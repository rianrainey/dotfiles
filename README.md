# Dotfiles

This uses [Stow](https://www.gnu.org/software/stow/) to symlink my dotfiles

## Guidance

Put application dotfiles in respective folder. For example, `~/dotfiles/vim/.vimrc` would have all the symlinked dotfiles for `~/.vimrc` on my machine. Stow symlinks up 1 directory, fyi. You might be able to use target directories to get around that design.


## Usage

```
cd ~
git clone git@github.com:rianrainey/dotfiles.git
stow git # Or whatever module you what to symlink
```

## Steps For New Install

```
sh osx-settings-configure.sh
sh setup.sh
```

## Other Steps

1. [Get iTerm Color Schemes](http://iterm2colorschemes.com/)
