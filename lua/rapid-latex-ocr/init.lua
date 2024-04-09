local M = {}
M.delimiters = {
  ["None"] = {left = "", right = ""},
  ["Dollar"] = {left = "$", right = "$"},
  ["Double Dollar"] = {left = "$$", right = "$$"},
}
local function is_valid_delimiter(value)
    -- Check if the value is a table with 'left' and 'right' keys
    if type(value) ~= "table" or not value.left or not value.right then
        return false, "Delimiter must be a table with 'left' and 'right' keys."
    end
    -- Check for valid characters that won't cause issues in JSON encoding/decoding
    if type(value.left) ~= "string" or type(value.right) ~= "string" then
        return false, "Delimiter 'left' and 'right' values must be strings."
    end
    return true
end
function M.setup(user_delimiters)
    if user_delimiters ~= nil then
      for key, value in pairs(user_delimiters) do
          local is_valid, err_msg = is_valid_delimiter(value)
          if is_valid then
              M.delimiters[key] = value
          else
              vim.api.nvim_err_write("Error: Delimiter '" .. key .. "' is invalid. " .. err_msg .. "\n")
          end
      end
    end
    -- Attempt to encode to JSON to catch any potential issues early
    local success, encoded = pcall(vim.fn.json_encode, M.delimiters)
    if not success then
        vim.api.nvim_err_write("Error: Failed to encode delimiters to JSON. Please check delimiter definitions.\n")
        return
    end
    local delimiters_vim_dict = vim.fn.json_decode(encoded)
    vim.api.nvim_call_function('SetupDelimiters', {delimiters_vim_dict})

    vim.api.nvim_create_user_command('ImageToLatex', function()
      vim.fn['ImageToLatex']('None')
    end, {})
end
return M
