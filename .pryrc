# Enable color
Pry.config.color = true

# disable pager for long output
Pry.config.pager = false

# set editor to textmate
Pry.config.editor = "mvim"

if defined?(PryDebugger)
  Pry.commands.alias_command 'c', 'continue'
  Pry.commands.alias_command 's', 'step'
  Pry.commands.alias_command 'n', 'next'
  Pry.commands.alias_command 'f', 'finish'
end
