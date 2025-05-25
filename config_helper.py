#!/usr/bin/env python3
"""
DZMM插件配置助手
帮助用户生成正确的JSON配置字符串
"""

import json

def generate_personas_config():
    """生成角色配置"""
    print("=== 角色配置生成器 ===")
    personas = {}
    
    # 默认角色
    personas["default"] = "你是一个有帮助的AI助手。"
    
    while True:
        print(f"\n当前已配置的角色：")
        for name, prompt in personas.items():
            print(f"  {name}: {prompt[:50]}...")
        
        print("\n选项：")
        print("1. 添加新角色")
        print("2. 修改现有角色")
        print("3. 删除角色")
        print("4. 生成配置字符串")
        print("5. 退出")
        
        choice = input("\n请选择操作 (1-5): ").strip()
        
        if choice == "1":
            name = input("请输入角色名称: ").strip()
            if name:
                prompt = input("请输入角色描述: ").strip()
                if prompt:
                    personas[name] = prompt
                    print(f"✅ 角色 '{name}' 添加成功")
                else:
                    print("❌ 角色描述不能为空")
            else:
                print("❌ 角色名称不能为空")
        
        elif choice == "2":
            name = input("请输入要修改的角色名称: ").strip()
            if name in personas:
                print(f"当前描述: {personas[name]}")
                new_prompt = input("请输入新的角色描述: ").strip()
                if new_prompt:
                    personas[name] = new_prompt
                    print(f"✅ 角色 '{name}' 修改成功")
                else:
                    print("❌ 角色描述不能为空")
            else:
                print(f"❌ 角色 '{name}' 不存在")
        
        elif choice == "3":
            name = input("请输入要删除的角色名称: ").strip()
            if name == "default":
                print("❌ 不能删除默认角色")
            elif name in personas:
                del personas[name]
                print(f"✅ 角色 '{name}' 删除成功")
            else:
                print(f"❌ 角色 '{name}' 不存在")
        
        elif choice == "4":
            config_str = json.dumps(personas, ensure_ascii=False)
            print(f"\n=== 角色配置字符串 ===")
            print(config_str)
            print("\n请将上述字符串复制到astrbot配置界面的 'personas' 字段中")
            return config_str
        
        elif choice == "5":
            return None
        
        else:
            print("❌ 无效选择，请重新输入")

def generate_api_keys_config():
    """生成API密钥配置"""
    print("=== API密钥配置生成器 ===")
    api_keys = {}
    
    while True:
        print(f"\n当前已配置的API密钥：")
        for name, key in api_keys.items():
            masked_key = key[:8] + "..." + key[-4:] if len(key) > 12 else key
            print(f"  {name}: {masked_key}")
        
        print("\n选项：")
        print("1. 添加新API密钥")
        print("2. 修改现有API密钥")
        print("3. 删除API密钥")
        print("4. 生成配置字符串")
        print("5. 退出")
        
        choice = input("\n请选择操作 (1-5): ").strip()
        
        if choice == "1":
            name = input("请输入API密钥名称 (如: default, backup, premium): ").strip()
            if name:
                key = input("请输入API密钥: ").strip()
                if key:
                    api_keys[name] = key
                    print(f"✅ API密钥 '{name}' 添加成功")
                else:
                    print("❌ API密钥不能为空")
            else:
                print("❌ API密钥名称不能为空")
        
        elif choice == "2":
            name = input("请输入要修改的API密钥名称: ").strip()
            if name in api_keys:
                current_key = api_keys[name]
                masked_key = current_key[:8] + "..." + current_key[-4:] if len(current_key) > 12 else current_key
                print(f"当前密钥: {masked_key}")
                new_key = input("请输入新的API密钥: ").strip()
                if new_key:
                    api_keys[name] = new_key
                    print(f"✅ API密钥 '{name}' 修改成功")
                else:
                    print("❌ API密钥不能为空")
            else:
                print(f"❌ API密钥 '{name}' 不存在")
        
        elif choice == "3":
            name = input("请输入要删除的API密钥名称: ").strip()
            if name in api_keys:
                del api_keys[name]
                print(f"✅ API密钥 '{name}' 删除成功")
            else:
                print(f"❌ API密钥 '{name}' 不存在")
        
        elif choice == "4":
            if not api_keys:
                print("❌ 请至少配置一个API密钥")
                continue
            
            config_str = json.dumps(api_keys, ensure_ascii=False)
            print(f"\n=== API密钥配置字符串 ===")
            print(config_str)
            print("\n请将上述字符串复制到astrbot配置界面的 'api_keys' 字段中")
            return config_str
        
        elif choice == "5":
            return None
        
        else:
            print("❌ 无效选择，请重新输入")

def main():
    """主函数"""
    print("DZMM插件配置助手")
    print("================")
    print("此工具帮助您生成正确的JSON配置字符串")
    
    while True:
        print("\n主菜单：")
        print("1. 配置角色 (personas)")
        print("2. 配置API密钥 (api_keys)")
        print("3. 退出")
        
        choice = input("\n请选择操作 (1-3): ").strip()
        
        if choice == "1":
            generate_personas_config()
        elif choice == "2":
            generate_api_keys_config()
        elif choice == "3":
            print("感谢使用DZMM插件配置助手！")
            break
        else:
            print("❌ 无效选择，请重新输入")

if __name__ == "__main__":
    main()
