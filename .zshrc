
# Path to your oh-my-zsh configuration.
ZSH=$HOME/.oh-my-zsh

export EDITOR='mvim'

# Set name of the theme to load.
# Look in ~/.oh-my-zsh/themes/
# Optionally, if you set this to "random", it'll load a random theme each
# time that oh-my-zsh is loaded.
ZSH_THEME="bullet-train"

# Which plugins would you like to load? (plugins can be found in ~/.oh-my-zsh/plugins/*)
# Custom plugins may be added to ~/.oh-my-zsh/custom/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
plugins=(git osx)

CONFIG_PATH="Dropbox (Personal)/Personal/sharedConfiguration/dotFiles"

source $ZSH/oh-my-zsh.sh
unsetopt correct

# Load all my custom aliases
source $HOME/$CONFIG_PATH/.alias

# Change colors of listing directory contents
# Good tutorial at: http://meefirst.blogspot.com/2012/04/changing-colour-of-directory-listings.html
LSCOLORS="BxCxcxdxbxegedabagacad"
export LSCOLORS

# Homebrew path
#homebrew=/usr/local/bin:/usr/local/sbin
#export PATH=$homebrew:$PATH

# Boxen
source /opt/boxen/env.sh

# AWS CLI
source /opt/boxen/homebrew/share/zsh/site-functions/_aws

export TERM="xterm-256color"
