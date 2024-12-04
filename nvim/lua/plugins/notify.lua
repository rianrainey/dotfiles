return {
  "rcarriga/nvim-notify",
  opts = {
    timeout = 3000,
    --   max_height = 10,
    render = "default",
    stages = "slide",
  },
  config = function(_, opts)
    require("notify").setup(opts)
    vim.notify = require("notify")
  end,
  keys = {
    {
      "<leader>un",
      function()
        require("notify").dismiss({ silent = true, pending = true })
      end,
      desc = "Dismiss all Notifications",
    },
  },
}
