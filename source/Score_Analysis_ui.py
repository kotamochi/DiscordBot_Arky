import os
import discord
from discord import ui
import Score_Analysis 
import pandas as pd
import asyncio


class StartButton(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="分析開始!!", style=discord.ButtonStyle.success)
    async def start(self, button: discord.ui.Button, interaction: discord.Interaction):
        """処理を進める"""
        if await self.botrole_check(button):
            await Score_Analysis.score_analysis(button)
        else:
            await button.response.send_message("Botの使い方を確認してないから使えないよ。確認してきてね！", ephemeral=True)

    async def botrole_check(self, ctx):
        """特定のロールが付与されているか"""
        role = ctx.guild.get_role(int(os.environ["BOTROLE_ID"]))
        if role in ctx.user.roles:
            return True
        else:
            return False


class CheckButton(ui.View):
    """選択のチェックボタン"""
    def __init__(self, ctx, channel=None, text=None):
        self.ctx = ctx
        self.channel = channel
        self.text = text
        super().__init__(timeout=None)
    
    @ui.button(label="OK", style=discord.ButtonStyle.success)
    async def ok(self, button: discord.ui.Button, interaction: discord.Interaction):
        """処理を進める"""
        await button.response.edit_message(content="決定したよ！", view=None)
        await Score_Analysis.namecheck(button, self.channel, self.text)
        
    @ui.button(label="やり直す", style=discord.ButtonStyle.gray)
    async def retry(self, button: discord.ui.Button, interaction: discord.Interaction):
        """やり直しさせる"""
        await button.response.edit_message(content="名前の再入力を行うよ", view=None)
        await Score_Analysis.signup(button, self.channel)


class MenuButten(ui.View):
    """データ分析選択ボタン"""
    def __init__(self):
        self.delete_flg = True
        super().__init__(timeout=None)
    
    @ui.button(label="スコア登録(更新)", style=discord.ButtonStyle.success)
    async def score_regist(self, button: discord.ui.Button, interaction: discord.Interaction):
        """データを登録する"""
        self.delete_flg = False
        await button.response.edit_message(content="データ登録を選択したよ！",view=None)
        await asyncio.sleep(1)
        await Score_Analysis.file_register(button, button.user)
        
        
    @ui.button(label="スコア分析", style=discord.ButtonStyle.blurple)
    async def analysis(self, button: discord.ui.Button, interaction: discord.Interaction):
        """スコア分析を行う"""
        self.delete_flg = False
        await button.response.edit_message(content="スコア分析を選択したよ！",view=None)
        await asyncio.sleep(1)
        try:
            data = await Score_Analysis.file_load(button.user) #スコア読み込み
            await button.followup.send("分析を開始するね")
            await Score_Analysis.analysis(button, data) #分析
        except FileNotFoundError:
            #ファイルが存在しない時の処理
            await button.followup.send("ファイルが登録されていないよ、先に「スコア登録(更新)」を行ってね！")
            #待機後、メニューを表示
            await asyncio.sleep(2)
            await Score_Analysis.start_menu(button, button.channel)
            
    
    @ui.button(label="ベスト枠", style=discord.ButtonStyle.blurple)
    async def bestplays(self, button: discord.ui.Button, interaction: discord.Interaction):
        """曲レートtop50曲を表示"""
        self.delete_flg = False
        await button.response.edit_message(content="べ枠Top50を選択したよ！",view=None)
        try:
            data = await Score_Analysis.file_load(button.user) #スコア読み込み
            await Score_Analysis.bestplays_50(button, data)
        except FileNotFoundError:
            #ファイルが存在しない時の処理
            await button.followup.send("ファイルが登録されていないよ、先に「スコア登録(更新)」を行ってね！")
            #待機後、メニューを表示
            await asyncio.sleep(2)
            await Score_Analysis.start_menu(button, button.channel)
            
    
    @ui.button(label="曲別内部失点", style=discord.ButtonStyle.blurple)
    async def precision(self, button: discord.ui.Button, interaction: discord.Interaction):
        """レべルごとに各曲の内部精度失点数を表示"""
        self.delete_flg = False
        await button.response.edit_message(content="内部精度一覧を選択したよ！",view=None)
        try:
            #ファイル確認用に読み込み
            data = await Score_Analysis.file_load(button.user) #スコア読み込み
            view = MusicLevelSerect(button)
            await button.channel.send(content="難易度を選択すると内部失点が表示されるよ", view=view)
        except FileNotFoundError:
            #ファイルが存在しない時の処理
            await button.followup.send("ファイルが登録されていないよ、先に「スコア登録(更新)」を行ってね！")
            #待機後、メニューを表示
            await asyncio.sleep(2)
            await Score_Analysis.start_menu(button, button.channel)
            

    @ui.button(label="終了する", style=discord.ButtonStyle.gray)
    async def stop(self, button: discord.ui.Button, interaction: discord.Interaction):
        """データ分析モードを終了する"""
        self.delete_flg = False
        await button.response.edit_message(content="データ分析を終了するよ、お疲れ様～～",view=None)
        await asyncio.sleep(3)
        await button.channel.delete()
        

class MusicLevelSerect(ui.View):
    """レベル選択ボタン"""
    def __init__(self, ctx):
        self.delete_flg = True
        self.channel = ctx.channel
        super().__init__(timeout=360)
        

    @discord.ui.select(cls=discord.ui.Select, placeholder="精度失点を表示する難易度を選んでね",options=[discord.SelectOption(label="ALL"), 
                                                                                                  discord.SelectOption(label="7"),
                                                                                                  discord.SelectOption(label="7+"),
                                                                                                  discord.SelectOption(label="8"),
                                                                                                  discord.SelectOption(label="8+"),
                                                                                                  discord.SelectOption(label="9"),
                                                                                                  discord.SelectOption(label="9+"),
                                                                                                  discord.SelectOption(label="10"),
                                                                                                  discord.SelectOption(label="10+"),
                                                                                                  discord.SelectOption(label="11"),
                                                                                                  discord.SelectOption(label="11+"),
                                                                                                  discord.SelectOption(label="12")]
                                                                                                  )
    async def levelselect(self, interaction: discord.Interaction, select: discord.ui.Select):
        """レベルを選択して表示"""
        self.delete_flg = False
        # 選択レベルを取得
        level = select.values[0]
        await interaction.response.edit_message(content = f"{interaction.user.display_name}さんのLevel{level}内部失点一覧\n", view=None)
        # スコア読み込み
        data = await Score_Analysis.file_load(interaction.user)
        # 計算
        await Score_Analysis.pure_precision(interaction, data, level)
        
        
    async def on_timeout(self):
        """タイムアウトの処理"""
        # 操作後であったら何もしない
        if self.delete_flg:
            #10分間無操作ならスレッド削除
            await self.channel.send("10分間操作されなかったからスレッドを削除するよ、またね！")
            await asyncio.sleep(1)
            await self.channel.delete()