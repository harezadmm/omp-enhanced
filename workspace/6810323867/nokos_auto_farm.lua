-- Nokos Auto Farm Script
-- Auto-farms eggs/pets in Legends of Speed until Nokos is obtained
-- Compatible with most Roblox executors

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local VirtualUser = game:GetService("VirtualUser")
local LocalPlayer = Players.LocalPlayer

-- Anti-AFK
LocalPlayer.Idled:Connect(function()
    VirtualUser:CaptureController()
    VirtualUser:ClickButton2(Vector2.new())
end)

-- Configuration
local Config = {
    Enabled = true,
    TargetPet = "Nokos",
    AutoHatch = true,
    AutoCollectOrbs = true,
    AutoRebirth = false,
    TeleportToEggZone = true,
    EggType = "Chaos Egg", -- Change to target egg type
    FastHatch = true,
    NotifyOnSuccess = true
}

-- State
local Found = false
local HatchCount = 0
local StartTime = tick()

-- GUI Setup
local ScreenGui = Instance.new("ScreenGui")
ScreenGui.Name = "NokosAutoFarm"
ScreenGui.ResetOnSpawn = false
ScreenGui.Parent = game:GetService("CoreGui")

local MainFrame = Instance.new("Frame")
MainFrame.Size = UDim2.new(0, 280, 0, 320)
MainFrame.Position = UDim2.new(0.5, -140, 0.5, -160)
MainFrame.BackgroundColor3 = Color3.fromRGB(25, 25, 25)
MainFrame.BorderSizePixel = 0
MainFrame.Parent = ScreenGui

local UICorner = Instance.new("UICorner")
UICorner.CornerRadius = UDim.new(0, 8)
UICorner.Parent = MainFrame

local Title = Instance.new("TextLabel")
Title.Size = UDim2.new(1, 0, 0, 40)
Title.BackgroundColor3 = Color3.fromRGB(35, 35, 35)
Title.BorderSizePixel = 0
Title.Text = "🐎 Nokos Auto Farm"
Title.TextColor3 = Color3.fromRGB(255, 255, 255)
Title.Font = Enum.Font.GothamBold
Title.TextSize = 16
Title.Parent = MainFrame

local TitleCorner = Instance.new("UICorner")
TitleCorner.CornerRadius = UDim.new(0, 8)
TitleCorner.Parent = Title

local StatusLabel = Instance.new("TextLabel")
StatusLabel.Size = UDim2.new(1, -20, 0, 60)
StatusLabel.Position = UDim2.new(0, 10, 0, 50)
StatusLabel.BackgroundTransparency = 1
StatusLabel.Text = "Status: Initializing..."
StatusLabel.TextColor3 = Color3.fromRGB(200, 200, 200)
StatusLabel.Font = Enum.Font.Gotham
StatusLabel.TextSize = 13
StatusLabel.TextWrapped = true
StatusLabel.TextYAlignment = Enum.TextYAlignment.Top
StatusLabel.Parent = MainFrame

local StatsLabel = Instance.new("TextLabel")
StatsLabel.Size = UDim2.new(1, -20, 0, 80)
StatsLabel.Position = UDim2.new(0, 10, 0, 120)
StatsLabel.BackgroundTransparency = 1
StatsLabel.Text = "Hatches: 0\nTime: 0s\nSpeed: 0/min"
StatsLabel.TextColor3 = Color3.fromRGB(180, 180, 180)
StatsLabel.Font = Enum.Font.GothamMono
StatsLabel.TextSize = 12
StatsLabel.TextYAlignment = Enum.TextYAlignment.Top
StatsLabel.Parent = MainFrame

local ToggleButton = Instance.new("TextButton")
ToggleButton.Size = UDim2.new(1, -20, 0, 35)
ToggleButton.Position = UDim2.new(0, 10, 0, 210)
ToggleButton.BackgroundColor3 = Color3.fromRGB(46, 204, 113)
ToggleButton.Text = "Running"
ToggleButton.TextColor3 = Color3.fromRGB(255, 255, 255)
ToggleButton.Font = Enum.Font.GothamBold
ToggleButton.TextSize = 14
ToggleButton.Parent = MainFrame

local ToggleCorner = Instance.new("UICorner")
ToggleCorner.CornerRadius = UDim.new(0, 6)
ToggleCorner.Parent = ToggleButton

local CloseButton = Instance.new("TextButton")
CloseButton.Size = UDim2.new(1, -20, 0, 35)
CloseButton.Position = UDim2.new(0, 10, 0, 255)
CloseButton.BackgroundColor3 = Color3.fromRGB(231, 76, 60)
CloseButton.Text = "Stop & Close"
CloseButton.TextColor3 = Color3.fromRGB(255, 255, 255)
CloseButton.Font = Enum.Font.GothamBold
CloseButton.TextSize = 14
CloseButton.Parent = MainFrame

local CloseCorner = Instance.new("UICorner")
CloseCorner.CornerRadius = UDim.new(0, 6)
CloseCorner.Parent = CloseButton

-- Dragging functionality
local dragging, dragInput, dragStart, startPos

local function update(input)
    local delta = input.Position - dragStart
    MainFrame.Position = UDim2.new(startPos.X.Scale, startPos.X.Offset + delta.X, startPos.Y.Scale, startPos.Y.Offset + delta.Y)
end

Title.InputBegan:Connect(function(input)
    if input.UserInputType == Enum.UserInputType.MouseButton1 then
        dragging = true
        dragStart = input.Position
        startPos = MainFrame.Position
        
        input.Changed:Connect(function()
            if input.UserInputState == Enum.UserInputState.End then
                dragging = false
            end
        end)
    end
end)

Title.InputChanged:Connect(function(input)
    if input.UserInputType == Enum.UserInputType.MouseMovement then
        dragInput = input
    end
end)

RunService.Heartbeat:Connect(function()
    if dragging and dragInput then
        update(dragInput)
    end
end)

-- Button handlers
ToggleButton.MouseButton1Click:Connect(function()
    Config.Enabled = not Config.Enabled
    if Config.Enabled then
        ToggleButton.Text = "Running"
        ToggleButton.BackgroundColor3 = Color3.fromRGB(46, 204, 113)
    else
        ToggleButton.Text = "Paused"
        ToggleButton.BackgroundColor3 = Color3.fromRGB(149, 165, 166)
    end
end)

CloseButton.MouseButton1Click:Connect(function()
    Config.Enabled = false
    ScreenGui:Destroy()
end)

-- Utility functions
local function UpdateStatus(text)
    StatusLabel.Text = "Status: " .. text
end

local function UpdateStats()
    local elapsed = tick() - StartTime
    local rate = elapsed > 0 and (HatchCount / elapsed * 60) or 0
    StatsLabel.Text = string.format("Hatches: %d\nTime: %ds\nSpeed: %.1f/min", 
        HatchCount, math.floor(elapsed), rate)
end

local function Notify(title, text, duration)
    game:GetService("StarterGui"):SetCore("SendNotification", {
        Title = title,
        Text = text,
        Duration = duration or 5
    })
end

-- Game-specific functions
local function GetPetInventory()
    local success, result = pcall(function()
        return LocalPlayer.PlayerGui:FindFirstChild("PetsInventoryGui") or 
               LocalPlayer.PlayerGui:FindFirstChild("Pets") or
               LocalPlayer:FindFirstChild("PetsFolder")
    end)
    return success and result or nil
end

local function HasNokos()
    local inventory = GetPetInventory()
    if not inventory then return false end
    
    for _, pet in pairs(inventory:GetDescendants()) do
        if pet:IsA("StringValue") or pet:IsA("TextLabel") or pet:IsA("TextButton") then
            if string.find(string.lower(tostring(pet.Name)), "nokos") or 
               string.find(string.lower(tostring(pet.Text or "")), "nokos") then
                return true
            end
        end
    end
    return false
end

local function TeleportToEgg()
    pcall(function()
        local eggLocations = workspace:FindFirstChild("EggLocations") or workspace:FindFirstChild("Eggs")
        if eggLocations then
            for _, egg in pairs(eggLocations:GetChildren()) do
                if string.find(string.lower(egg.Name), string.lower(Config.EggType)) or
                   string.find(string.lower(egg.Name), "chaos") then
                    LocalPlayer.Character:SetPrimaryPartCFrame(egg.CFrame + Vector3.new(0, 5, 0))
                    return true
                end
            end
        end
    end)
end

local function HatchEgg()
    local success = false
    
    -- Method 1: Remote event
    pcall(function()
        local remotes = ReplicatedStorage:FindFirstChild("Remotes") or ReplicatedStorage:FindFirstChild("Events")
        if remotes then
            for _, remote in pairs(remotes:GetDescendants()) do
                if remote:IsA("RemoteEvent") or remote:IsA("RemoteFunction") then
                    if string.find(string.lower(remote.Name), "hatch") or 
                       string.find(string.lower(remote.Name), "open") or
                       string.find(string.lower(remote.Name), "egg") then
                        if remote:IsA("RemoteEvent") then
                            remote:FireServer(Config.EggType, 1)
                            remote:FireServer("Chaos", 1)
                        else
                            remote:InvokeServer(Config.EggType, 1)
                            remote:InvokeServer("Chaos", 1)
                        end
                        success = true
                    end
                end
            end
        end
    end)
    
    -- Method 2: Click detector
    pcall(function()
        local eggLocations = workspace:FindFirstChild("EggLocations") or workspace:FindFirstChild("Eggs")
        if eggLocations then
            for _, egg in pairs(eggLocations:GetDescendants()) do
                if egg:IsA("ClickDetector") then
                    fireclickdetector(egg)
                    success = true
                end
            end
        end
    end)
    
    -- Method 3: ProximityPrompt
    pcall(function()
        local eggLocations = workspace:FindFirstChild("EggLocations") or workspace:FindFirstChild("Eggs")
        if eggLocations then
            for _, prompt in pairs(eggLocations:GetDescendants()) do
                if prompt:IsA("ProximityPrompt") then
                    fireproximityprompt(prompt)
                    success = true
                end
            end
        end
    end)
    
    return success
end

local function CollectOrbs()
    pcall(function()
        local orbs = workspace:FindFirstChild("Orbs") or workspace:FindFirstChild("Collectibles")
        if orbs then
            for _, orb in pairs(orbs:GetChildren()) do
                if orb:IsA("BasePart") and LocalPlayer.Character and LocalPlayer.Character.PrimaryPart then
                    local distance = (orb.Position - LocalPlayer.Character.PrimaryPart.Position).Magnitude
                    if distance < 100 then
                        orb.CFrame = LocalPlayer.Character.PrimaryPart.CFrame
                    end
                end
            end
        end
    end)
end

-- Main loop
UpdateStatus("Starting auto-farm...")
wait(2)

spawn(function()
    while wait(0.5) do
        if Config.Enabled and not Found then
            UpdateStats()
            
            -- Check if we already have Nokos
            if HasNokos() then
                Found = true
                UpdateStatus("✅ NOKOS FOUND!")
                ToggleButton.Text = "✅ Success!"
                ToggleButton.BackgroundColor3 = Color3.fromRGB(241, 196, 15)
                if Config.NotifyOnSuccess then
                    Notify("🎉 Success!", "Nokos has been obtained!", 10)
                end
                break
            end
            
            -- Auto-farm logic
            if Config.AutoHatch then
                if Config.TeleportToEggZone then
                    TeleportToEgg()
                    wait(0.3)
                end
                
                local hatched = HatchEgg()
                if hatched then
                    HatchCount = HatchCount + 1
                    UpdateStatus("Hatching... (" .. HatchCount .. " attempts)")
                    
                    if Config.FastHatch then
                        wait(0.1)
                    else
                        wait(1)
                    end
                else
                    UpdateStatus("Searching for hatch method...")
                    wait(2)
                end
            end
            
            if Config.AutoCollectOrbs then
                CollectOrbs()
            end
        end
    end
end)

-- Stats updater
spawn(function()
    while wait(1) do
        if Config.Enabled and not Found then
            UpdateStats()
        end
    end
end)

UpdateStatus("Ready! Farming for Nokos...")
Notify("Nokos Auto Farm", "Script loaded successfully!", 5)
