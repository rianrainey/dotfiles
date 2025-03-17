-- return {
--   {
--     "williamboman/mason.nvim",
--     config = function()
--       require("mason").setup()
--     end,
--   },
--   {
--     "williamboman/mason-lspconfig.nvim",
--     config = function()
--       require("mason-lspconfig").setup()
--     end,
--   },
--   {
--     "neovim/nvim-lspconfig",
--     config = function()
--       local lspconfig = require("lspconfig")
--       lspconfig.lua_ls.setup()
--     end,
--   },
-- }
-- Typecraft
-- https://youtu.be/S-xzYgTLVJE?si=MGNvzcZ6ksE57r5C&t=539
return {
  {
    "williamboman/mason.nvim",
    dependencies = {
      "williamboman/mason-lspconfig.nvim",
      "neovim/nvim-lspconfig",
    },
    config = function()
      require("mason").setup()
      require("mason-lspconfig").setup({
        ensure_installed = {
          "lua_ls",
          "ruby_lsp", -- ruby
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
}
