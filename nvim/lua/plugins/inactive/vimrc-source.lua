--return {
--  keys = {
--    {
--      "<leader>vr",
--      function()
--        vim.cmd("source $MYVIMRC")
--        vim.notify("Neovim config successfully reloaded!", "info", {
--          title = "Config Reload",
--          timeout = 1000,
--        })
--      end,
--      desc = "Reload nvim config - init.lua",
--    },
--  },
--}