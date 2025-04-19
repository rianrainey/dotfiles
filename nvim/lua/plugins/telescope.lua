return {
  "nvim-telescope/telescope.nvim",
  dependencies = { "nvim-telescope/telescope-live-grep-args.nvim" },
  config = function(_, opts)
    -- Load Telescope and its extensions
    require("telescope").setup(opts)
    require("telescope").load_extension("live_grep_args")

    -- Keymap to search for word under cursor (editable prompt)
    vim.keymap.set("n", "<leader>#", function()
      local word = vim.fn.expand("<cword>")
      require("telescope.builtin").live_grep({ default_text = word })
    end, { desc = "Live Grep (editable) word under cursor" })
  end,
  keys = {
    -- Other keymaps (keep these if needed)
    {
      "<leader>fp",
      function()
        require("telescope.builtin").find_files({ cwd = require("lazy.core.config").options.root })
      end,
      desc = "Find Plugin File",
    },
  },

  -- change some options
  -- opts = {
  --   defaults = {
  --     layout_strategy = "horizontal",
  --     layout_config = { prompt_position = "top" },
  --     sorting_strategy = "ascending",
  --     winblend = 0,
  --   },
  -- },
}
