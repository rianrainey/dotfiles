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
  hub
  mackup
  node
  python
  rename
  tree
  wget
)

echo "Installing binaries..."
brew install ${binaries[@]}

echo "Brew cleaning..."
brew cleanup

######
# Brew Casks
######

brew install caskroom/cask/brew-cask

apps=(
  1password
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
  flash
  flux
  firefox
  google-chrome
  harvest
  hipchat
  iterm2
  macvim
  mailplane
  monolingual
  notational-velocity
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
  ynab
)

# Install apps to /Applications
# Default is: /Users/$user/Applications
echo "installing apps..."
brew cask install --appdir="/Applications" ${apps[@]}

#########################################################################
# Alfred
# One thing you may notice if you're an Alfred user is that you cannot
# actually launch these apps from Alfred because the actual location
# of the app is not in /Applications but in /opt/homebrew-cask/Caskroom/.

# To add this path to Alfred, you can run the following command:
##########################################################################

brew cask alfred link

##########################################################################
# Fonts
##########################################################################

# fonts
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
source ~/.zshrc
