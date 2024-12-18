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

-- kj remap to Esc
vim.keymap.set("i", "kj", "<Esc>", { noremap = true })

-- Start rubocop
vim.opt.signcolumn = "yes"

vim.api.nvim_create_autocmd("FileType", {
  pattern = "ruby",
  callback = function()
    vim.lsp.start({
      name = "rubocop",
      cmd = { "bundle", "exec", "rubocop", "--lsp" },
    })
  end,
})

-- Enable auto-formatting on save
vim.api.nvim_create_autocmd("BufWritePre", {
  pattern = "*",
  callback = function(args)
    vim.lsp.buf.format({ bufnr = args.buf })
  end,
})

-- Which Key
require("which-key").setup({
  preset = "modern", -- Use "classic", "modern", or "helix"
})

-- telescope
-- require("telescope").setup({
--   defaults = {},
--   pickers = {
--     find_files = {
--       theme = "dropdown",
--     },
--   },
--   extensions = {},
-- })

------------------------ Harpoon ---------------------------------------
local harpoon = require("harpoon")
harpoon:setup()

vim.keymap.set("n", "<leader>a", function()
  harpoon:list():add()
end)

-- vim.keymap.set("n", "<leader>hr", function()
--   harpoon:list():remove()
-- end)

vim.keymap.set("n", "<C-e>", function()
  harpoon.ui:toggle_quick_menu(harpoon:list())
end)

-- vim.keymap.set("n", "<C-h>", function()
--   harpoon:list():select(1)
-- end)
-- vim.keymap.set("n", "<C-t>", function()
--   harpoon:list():select(2)
-- end)
-- vim.keymap.set("n", "<C-n>", function()
--   harpoon:list():select(3)
-- end)
-- vim.keymap.set("n", "<C-s>", function()
--   harpoon:list():select(4)
-- end)
--
-- -- Toggle previous & next buffers stored within Harpoon list
-- vim.keymap.set("n", "<C-S-P>", function()
--   harpoon:list():prev()
-- end)
-- vim.keymap.set("n", "<C-S-N>", function()
--   harpoon:list():next()
-- end)

-- basic telescope configuration
-- local conf = require("telescope.config").values
-- local function toggle_telescope(harpoon_files)
--   local file_paths = {}
--   for _, item in ipairs(harpoon_files.items) do
--     table.insert(file_paths, item.value)
--   end
--
--   require("telescope.pickers")
--     .new({}, {
--       prompt_title = "Harpoon",
--       finder = require("telescope.finders").new_table({
--         results = file_paths,
--       }),
--       previewer = conf.file_previewer({}),
--       sorter = conf.generic_sorter({}),
--     })
--     :find()
-- end
--
-- vim.keymap.set("n", "<C-e>", function()
--   toggle_telescope(harpoon:list())
-- end, { desc = "Open harpoon window" })
--------------------- /Harpoon ------------------------------------------
