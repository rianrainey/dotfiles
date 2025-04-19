return {
  {
    "vim-test/vim-test",
    config = function()
      vim.g["test#strategy"] = "neovim"
      vim.g["test#neovim#term_position"] = "botright 30"

      vim.keymap.set("n", "<leader>tn", ":TestNearest<CR>", { silent = true })
      vim.keymap.set("n", "<leader>tf", ":TestFile<CR>", { silent = true })
      vim.keymap.set("n", "<leader>ta", ":TestSuite<CR>", { silent = true })
      vim.keymap.set("n", "<leader>tl", ":TestLast<CR>", { silent = true })
      vim.keymap.set("n", "<leader>tg", ":TestVisit<CR>", { silent = true })
    end,
  },
}
