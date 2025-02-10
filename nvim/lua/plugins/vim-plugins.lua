return {
  {
    "vim-test/vim-test",
    config = function()
      vim.g["test#strategy"] = "neovim"
      vim.g["test#neovim#term_position"] = "botright 15"

      -- Optional: Add keymaps for running tests
      vim.keymap.set("n", "<leader>tn", ":TestNearest<CR>", { silent = true })
      vim.keymap.set("n", "<leader>tf", ":TestFile<CR>", { silent = true })
      vim.keymap.set("n", "<leader>ta", ":TestSuite<CR>", { silent = true })
      vim.keymap.set("n", "<leader>tl", ":TestLast<CR>", { silent = true })
      vim.keymap.set("n", "<leader>tg", ":TestVisit<CR>", { silent = true })
      -- vim.keymap.set("n", "<leader>t", ":TestNearest<CR>", { silent = true })
      -- vim.keymap.set("n", "<leader>T", ":TestFile<CR>", { silent = true })
      -- vim.keymap.set("n", "<leader>a", ":TestSuite<CR>", { silent = true })
      -- vim.keymap.set("n", "<leader>l", ":TestLast<CR>", { silent = true })
      -- vim.keymap.set("n", "<leader>g", ":TestVisit<CR>", { silent = true })
    end,
  },
}
