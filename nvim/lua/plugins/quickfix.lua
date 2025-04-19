return {
  "kevinhwang91/nvim-bqf",
  event = "VeryLazy",
  config = function()
    require("bqf").setup({
      auto_enable = true,
      auto_resize_height = true,
      preview = {
        auto_preview = true,
        win_height = 12,
        win_vheight = 12,
        delay_syntax = 80,
        border_chars = { "┃", "┃", "━", "━", "┏", "┓", "┗", "┛", "█" },
        title = true,
        use_defaults = false,
        on_config_done = nil,
      },
      filter = {
        fzf = {
          fuzzy = true,
          override_generic_sorter = true,
          override_file_sorter = true,
          case_mode = "smart_case",
        },
      },
      func_map = {
        drop = "o",
        openc = "O",
        split = "<C-s>",
        tabdrop = "<C-t>",
        tabc = "<C-T>",
        vsplit = "<C-v>",
        ptogglemode = "z,",
        ptoggleitem = "p",
        ptoggleauto = "P",
        pscrollup = "<C-b>",
        pscrolldown = "<C-f>",
        pscrollorig = "zo",
        prevfile = "<C-p>",
        nextfile = "<C-n>",
        prevhist = "<",
        nexthist = ">",
        lastleave = "\"",
        stoggleup = "<S-Tab>",
        stoggledown = "<Tab>",
        stogglevm = "<Tab>",
        stogglebuf = "'<Tab>",
        sclear = "z<Tab>",
        filter = "zn",
        filterr = "zN",
        fzffilter = "zf",
        -- Use x instead of d for deletion to avoid conflict with which-key
        toggle_current_qf_item = "x",
      },
    })

    -- Create a global debug command
    vim.api.nvim_create_user_command("BqfDebug", function()
      local win_id = vim.fn.getqflist({winid = 0}).winid
      if win_id == 0 then
        vim.notify("No quickfix window open", vim.log.levels.ERROR)
        return
      end

      local buf_id = vim.api.nvim_win_get_buf(win_id)
      local which_key_disabled = vim.b[buf_id].which_key_disable or false
      vim.notify("Debug Info:\n" ..
                "Quickfix buffer ID: " .. buf_id .. "\n" ..
                "which_key_disable: " .. tostring(which_key_disabled))

      -- Check which-key config
      local status, which_key = pcall(require, "which-key")
      if status then
        local config = which_key.config or {}
        local disable_ft = (config.disable and config.disable.filetypes) or {}
        vim.notify("Which-key filetypes disabled: " .. vim.inspect(disable_ft))
      end
    end, {})

    -- Add a help message for the quickfix window and make it modifiable
    vim.api.nvim_create_autocmd("FileType", {
      pattern = "qf",
      callback = function()
        -- Make the quickfix window modifiable
        vim.opt_local.modifiable = true
        
        -- Add help keybinding
        vim.api.nvim_buf_set_keymap(0, "n", "?", "", {
          callback = function()
            vim.notify(
              "nvim-bqf Quickfix Keys:\n" ..
              "Tab: Enter action mode\n" ..
              "x: Delete item (after Tab)\n" ..
              "o: Open item\n" ..
              "p: Toggle preview\n" ..
              "zf: Filter items",
              vim.log.levels.INFO
            )
          end,
          noremap = true,
          silent = true,
        })
        
        -- Add a custom keybinding for deletion that ensures modifiable is on
        vim.api.nvim_buf_set_keymap(0, "n", "<Tab>x", "", {
          callback = function()
            -- Ensure the buffer is modifiable
            vim.opt_local.modifiable = true
            
            -- Call the bqf toggle function directly
            if vim.fn.exists("*bqf#action#toggle_current_qf_item") == 1 then
              vim.fn["bqf#action#toggle_current_qf_item"]()
            end
          end,
          noremap = true,
          silent = true,
        })

        -- Notify the user about the new keybinding
        vim.defer_fn(function()
          vim.notify("Use Tab+x to delete items in quickfix window (press ? for help)", vim.log.levels.INFO)
        end, 1000)
      end,
    })
  end,
}
