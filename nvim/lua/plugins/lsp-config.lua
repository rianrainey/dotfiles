return {
  {
    "williamboman/mason.nvim", -- installs and manages LSP servers
    dependencies = {
      "williamboman/mason-lspconfig.nvim", -- makes sure we have LSPs installed and configured
      "neovim/nvim-lspconfig", -- sets up LSP connection for Neovim
    },
    config = function()
      require("mason").setup()
      require("mason-lspconfig").setup({
        ensure_installed = {
          "lua_ls",
          "ruby_lsp", -- ruby. was causing errors
          "tsserver", -- typescript

          -- Add other LSPs you want to install
        },
        automatic_installation = true,
      })

      local lspconfig = require("lspconfig")
      require("mason-lspconfig").setup_handlers({
        function(server_name)
          lspconfig[server_name].setup({
            -- Default configuration for all language servers
            -- You can add server-specific settings here
          })
        end,
        -- Add any server-specific configurations here
        lspconfig.lua_ls.setup({}),
        lspconfig.ruby_lsp.setup({}),
        lspconfig.tsserver.setup({}),
      })
      vim.keymap.set("n", "K", "vim.lsp.buf.hover", {})
      vim.keymap.set("n", "gD", "vim.lsp.buf.definition", {})
      vim.keymap.set({ "n", "v" }, "<leader>ca", "vim.lsp.buf.code_action", {})
    end,
  },

  -- LazyVim preferred plugin for formatter. Already installed
  -- "stevearc/conform.nvim",
  -- opts = {},
  -- So is nvim-lint
}
