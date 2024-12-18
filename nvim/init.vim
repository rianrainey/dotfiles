vim.cmd([[
  set foldmethod=indent

  " Highlight trailing whitespace in red
  set listchars=tab:▸\ ,trail:· " configures how whitespace characters are displayed:
  set list " enables the display of these special characters
  highlight ExtraWhitespace ctermbg=red guibg=red
  match ExtraWhitespace /\s\+$/ "matches and highlights Any whitespace (\s+) At the end of lines ($)
  " TODO: red space shows up in neotree too :(

  " Triggers before writing a buffer (BufWritePre)
  " Applies to all files (*)
  " Substitutes trailing whitespace with nothing
  " The e flag suppresses errors if no matches found
  autocmd BufWritePre * :%s/\s\+$//e

  " Dont go into insert mode when adding new line above cursor
  nnoremap O O<Esc>

  " Turn off relative numbers by default. I think Lazyvim/Neovim turns these on
  set norelativenumber


]])
""""""""""""""""""""""""""
call plug#begin()

" List your plugins here
Plug 'vim-test/vim-test'

call plug#end()
