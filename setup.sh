###############
#
# Large influence from: http://lapwinglabs.com/blog/hacker-guide-to-setting-up-your-mac
#
################

# Check for Homebrew,
# Install if we don't have it
if test ! $(which brew); then
  echo "Installing homebrew..."
  ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
fi

# Update homebrew recipes
echo "Updating homebrew recipes..."
brew update

# Install GNU core utilities (those that come with OS X are outdated)
brew install coreutils

# Install GNU `find`, `locate`, `updatedb`, and `xargs`, g-prefixed
brew install findutils

# Install binaries
binaries=(
  ack
  ag
  ctags
  elixir
  gpg
  heroku
  hub
  mackup
  node
  postgresql
  python
  rbenv
  ruby-build
  reattach-to-user-namespace # Fix for tmux copy-paste
  rename
  tmux
  tree
  vim
  wget
)

echo "Installing binaries..."
brew install ${binaries[@]}

echo "Brew cleaning..."
brew cleanup

##########################################################################
# Brew Casks
##########################################################################

brew install caskroom/cask/brew-cask

apps=(
  airdisplay
  alfred
  anki
  bartender
  blue-jeans-browser-plugin
  blue-jeans-launcher
  cleanmymac
  dash
  disk-inventory-x
  dropbox
  evernote
  fiddler
  flash
  flux
  firefox
  google-drive
  harvest
  hipchat
  iterm2
  macvim
  mailplane
  monolingual
  notational-velocity
  pandora
  pg-commander
  sequel-pro
  sketch
  skype
  slack
  skype
  spectacle
  spotify
  sonos
  vagrant
  virtualbox
  vlc
)

# Install apps to /Applications
# Default is: /Users/$user/Applications
echo "installing apps..."
brew cask install --appdir="/Applications" ${apps[@]}

#########################################################################
# Tmate
#########################################################################
brew tap nviennot/tmate && \
brew install tmate

#########################################################################
# Alfred
# One thing you may notice if you're an Alfred user is that you cannot
# actually launch these apps from Alfred because the actual location
# of the app is not in /Applications but in /opt/homebrew-cask/Caskroom/.

# To add this path to Alfred, you can run the following command:
##########################################################################
# brew cask alfred link

##########################################################################
# Fonts
##########################################################################
brew tap caskroom/fonts

fonts=(
)

# install fonts
echo "installing fonts..."
brew cask install ${fonts[@]}


##########################################################################
# Symlink all dotfiles
##########################################################################

##########################################################################
# Install Zsh
##########################################################################
sh -c "$(curl -fsSL https://raw.github.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"

##########################################################################
# Install Janus
##########################################################################
#curl -L https://bit.ly/janus-bootstrap | bash # Uncomment if you need Janus

##########################################################################
# Link dotfiles to $HOME
##########################################################################
rake link

##########################################################################
# Install Powerline Fonts
# https://github.com/powerline/fonts
##########################################################################
git clone https://github.com/powerline/fonts.git ~/Downloads/fonts
cd ~/Downloads/fonts
sh install.sh

# Switch iTerm font to a Powerline Font (e.g. Meslo)
# TODO: Add ~/.vim to my dotfiles
# Download http://ethanschoonover.com/solarized for iTerm. Load Preset.
source ~/.zshrc
