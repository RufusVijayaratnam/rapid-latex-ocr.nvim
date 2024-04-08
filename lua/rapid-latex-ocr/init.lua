local M = {}
function M.setup()
    -- Register the "ImageToLatex" command directly here
    vim.api.nvim_create_user_command('ImageToLatex', function()
        -- Call the Python function exposed to Neovim
      vim.fn['ImageToLatex']()
    end, {})
    -- Debug message to confirm the Lua part is loaded
    print("Rapid LaTeX OCR plugin loaded successfully.")
end
return M
