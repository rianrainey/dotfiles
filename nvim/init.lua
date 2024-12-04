-- bootstrap lazy.nvim, LazyVim and your plugins
require("config.lazy")

-- Set up notify as the default notification system
vim.opt.termguicolors = true
vim.notify = require("notify")

-- Example keymap using notify
vim.keymap.set("n", "<leader>vr", function()
  vim.cmd("source $MYVIMRC")
  vim.notify("Neovim config successfully reloaded!", "info", {
    title = "Config Reload",
    timeout = 1000,
  })
end, { desc = "Reload nvim config" })

-- TODO
-- HACK
-- PERF

-- kj remap to Esc
vim.keymap.set("i", "kj", "<Esc>", { noremap = true })
