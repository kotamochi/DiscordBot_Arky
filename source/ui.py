import discord
from discord import ui
import Arcaea_command
import asyncio


class VSButton(ui.View):
    """対戦システムの選択ボタン"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="スコアバトル(1vs1)", style=discord.ButtonStyle.success, custom_id="Score_1vs1")
    async def score(self, button: discord.ui.Button, interaction: discord.Interaction):
        """1vs1"""
        await Arcaea_command.match_host(button, button.user.id, "0")

    @ui.button(label="EXスコアバトル(1vs1)", style=discord.ButtonStyle.blurple, custom_id="EXScore_1vs1")
    async def exscore(self, button: discord.ui.Button, interaction: discord.Interaction):
        """1vs1(EXScore)"""
        await Arcaea_command.match_host(button, button.user.id, "1")

    #@ui.button(label="ScoreBattle 2vs2", style=discord.ButtonStyle.blurple, custom_id="Score_2vs2")
    #async def score2(self, button: discord.ui.Button, interaction: discord.Interaction):
    #    """2vs2"""
    #    await Arcaea_command.match_host(button, button.user.id, "2")


class VSHostButton(ui.View):
    """対戦募集ボタン"""
    def __init__(self, user, kind, role_id, timeout=180):
        self.host = user
        self.kind = kind
        self.role_id = role_id
        self.stop_flg = True
        super().__init__(timeout=timeout)

    @ui.button(label="参加する", style=discord.ButtonStyle.success)
    async def vsstart(self, button: discord.ui.Button, interaction: discord.Interaction):
        #ロールが付与されてるか確認
        role = button.guild.get_role(self.role_id)
        if role in button.user.roles:
            #対戦中でないか確認
            if await Arcaea_command.state_check(button.user.id):
                return await button.response.send_message(f"あなたは対戦中、もしくは対戦ホスト中だよ", ephemeral=True)
            #対戦へ
            guest = button.user.id
            self.stop_flg = False
            await Arcaea_command.Arcaea_ScoreBattle(button, self.host, guest, self.kind)
        else:
            #Bot規約エラー
            return await button.response.send_message("Botの使い方を確認してないから使えないよ。確認してきてね！", ephemeral=True)

    @ui.button(label="取り消し(ホストのみ可)", style=discord.ButtonStyle.gray)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.host == button.user.id:
            #募集を取り消し
            await button.message.delete()
            #対戦フラグを消す
            await Arcaea_command.state_chenge(button.user.id, False)
            await button.response.send_message("募集を取り消したよ", ephemeral=True)
        else:
            await button.response.send_message("あなたはこの募集のホストじゃないよ。", ephemeral=True)


class VSStopbutton(ui.View):
    """対戦を途中終了する"""
    def __init__(self, user1, user2, timeout=180):
        self.player = [user1, user2]
        self.click = []
        self.vsstop = False
        super().__init__(timeout=timeout)

    @ui.button(label="終了", style=discord.ButtonStyle.gray)
    async def stop(self, button: discord.ui.Button, interaction: discord.Interaction):
        #対戦者かチェック
        flg = await self.check(button.user.id)
        if flg:
            #同じプレイヤーが再び押していないか
            if button.user.id in self.click:
                await button.response.send_message("もう押してるよ！", ephemeral=True)
            else:
                #ボタンをクリックした人を追加
                self.click.append(button.user.id)
                #二人ともがボタンを押したら終了処理を行う
                if len(self.click) == 2:
                    #ボタンを無効化
                    self.disabled = True
                    await button.response.edit_message(view=self)
                    await button.followup.send(f"{button.user.display_name}が終了を選択したよ\n対戦を終了するね")
                    self.vsstop = True #終了フラグを立てる
                    await asyncio.sleep(3) #インターバル
                    await button.channel.delete() #スレッドを閉じる
                    #対戦ステータスを変更
                    for user in self.player:
                        await Arcaea_command.state_chenge(user, False)
                else:
                    await button.response.send_message(f"{button.user.display_name}が終了を選択したよ")
        else:
            await button.response.send_message("きみは対戦者じゃないよ", ephemeral=True)

    async def check(self, user):
        """対戦者以外ではないか確認"""
        if user in self.player:
            return True #対戦者
        else:
            return False #それ以外


class VSMusicDifChoice(ui.View):
    """課題曲難易度選択ボタン"""
    def __init__(self, user1, user2, EX_flg, timeout=180):
        self.player = [user1, user2]
        self.click = []
        self.EX_flg = EX_flg
        self.FTR = False #各難易度の選択フラグ
        self.ETR = False
        self.BYD = False
        self.stop_flg = True
        super().__init__(timeout=timeout)

    @ui.button(label="FTR", style=discord.ButtonStyle.gray)
    async def ftr(self, button: discord.ui.Button, interaction: discord.Interaction):
        #対戦者かチェック
        if await self.check(button.user.id):

            if self.FTR == False:
                self.FTR = True
                self.children[0].style = discord.ButtonStyle.success
            else:
                self.FTR = False
                self.children[0].style = discord.ButtonStyle.gray

            #結果を表示
            await button.response.edit_message(view=self)
            await self.check_show_dif(button)
        else:
            await button.response.send_message("きみは対戦者じゃないよ", ephemeral=True)

    @ui.button(label="ETR", style=discord.ButtonStyle.gray)
    async def etr(self, button: discord.ui.Button, interaction: discord.Interaction):
        #対戦者かチェック
        if await self.check(button.user.id):

            if self.ETR == False:
                self.ETR = True
                self.children[1].style = discord.ButtonStyle.success
            else:
                self.ETR = False
                self.children[1].style = discord.ButtonStyle.gray
                
            #結果を表示
            await button.response.edit_message(view=self)
            await self.check_show_dif(button)
        else:
            await button.response.send_message("きみは対戦者じゃないよ", ephemeral=True)

    @ui.button(label="BYD", style=discord.ButtonStyle.gray)
    async def byd(self, button: discord.ui.Button, interaction: discord.Interaction):
        #対戦者かチェック
        if await self.check(button.user.id):
            if self.BYD == False:
                self.BYD = True
                self.children[2].style = discord.ButtonStyle.success
            else:
                self.BYD = False
                self.children[2].style = discord.ButtonStyle.gray

            #結果を表示
            await button.response.edit_message(view=self)
            await self.check_show_dif(button)
        else:
            await button.response.send_message("きみは対戦者じゃないよ", ephemeral=True)

    @ui.button(label="選択OK!!", style=discord.ButtonStyle.blurple)
    async def ok(self, button: discord.ui.Button, interaction: discord.Interaction):
        #対戦者かチェック
        if await self.check(button.user.id):
            #難易度が選ばれているか
            if self.FTR == False and self.ETR == False and self.BYD == False:
                await button.response.send_message("難易度が選ばれてないよ！！")
            else:
                #同じプレイヤーが再び押していないか
                if button.user.id in self.click:
                    await button.response.send_message("もう押してるよ！", ephemeral=True)
                else:
                    #ボタンをクリックした人を追加
                    self.click.append(button.user.id)
                    #二人ともがボタンを押したら処理を行う
                    if len(self.click) == 2:
                        #ボタンを無効化
                        self.children[0].disabled, self.children[1].disabled, self.children[2].disabled, self.children[3].disabled = True, True, True, True
                        await button.response.edit_message(view=self)
                        await button.followup.send(f"{button.user.display_name}がOKを選択したよ！ 難易度決定！")
                        #決定した難易度をListに
                        ls = []
                        if self.FTR:
                            ls.append("FTR")
                        if self.ETR:
                            ls.append("ETR")
                        if self.BYD:
                            ls.append("BYD")

                        #レベル選択へ
                        self.stop_flg = False
                        await Arcaea_command.s_sb_selectlevel(button, self.player[0], self.player[1], ls, self.EX_flg)
                    else:
                        await button.response.send_message(f"{button.user.display_name}がOKを選択したよ！")
                
        else:
            await button.response.send_message("きみは対戦者じゃないよ", ephemeral=True)

    async def check(self, user):
        """対戦者以外ではないか確認"""
        if user in self.player:
                return True #対戦者
        else:
            return False #それ以外
        
    async def check_show_dif(self, button):
        """今選択されている難易度を表示"""
        ls = []
        if self.FTR:
            ls.append("FTR")
        if self.ETR:
            ls.append("ETR")
        if self.BYD:
            ls.append("BYD")

        #返す文を作成
        msg = "選択されている難易度"
        for dif in ls:
            msg += f":{dif}"

        #送信
        await button.followup.send(msg)


class VSMusicLevelChoice(ui.View):
    """課題曲レベル選択ボタン"""
    def __init__(self, user1, user2, dif, EX_flg, timeout=180):
        self.player = [user1, user2]
        self.click = []
        self.EX_flg = EX_flg
        self.stop_flg = True
        #各レベルの選択フラグ
        self.level_dic = {"7":False,
                          "7+":False,
                          "8":False,
                          "8+":False,
                          "9":False,
                          "9+":False,
                          "10":False,
                          "10+":False,
                          "11":False,
                          "11+":False,
                          "12":False}
        self.dif = dif #選択されてる難易度
        self.FTR_Level = ["7", "7+", "8", "8+", "9", "9+", "10", "10+", "11"]
        self.ETR_Level = ["8", "8+", "9", "9+", "10", "10+", "11"]
        self.BYD_Level = ["9", "9+", "10", "10+", "11", "11+", "12"]
        super().__init__(timeout=timeout)

    @discord.ui.select(cls=discord.ui.Select, placeholder="課題曲のレベルを指定してね",options=[discord.SelectOption(label="ALL"), 
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
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select):
        level = select.values[0]
        #全レベル指定の場合
        if level == "ALL":
            #全レベルをTrueに
            #選択されたレベルが選択中の難易度にあるか
            if "FTR" in self.dif:
                for key in self.FTR_Level:
                    self.level_dic[key] = True
            if "ETR" in self.dif:
                for key in self.ETR_Level:
                    self.level_dic[key] = True
            if "BYD" in self.dif:
                for key in self.BYD_Level:
                    self.level_dic[key] = True
        else:
            #ALL以外
            #選択されたレベルが選択中の難易度にあるか
            if "FTR" in self.dif and level in self.FTR_Level:
                pass
            elif "ETR" in self.dif and level in self.ETR_Level:
                pass
            elif "BYD" in self.dif and level in self.BYD_Level:
                pass
            else:
                #ない場合
                return await interaction.response.send_message("選択した難易度にこのレベルはないよ")

            #レベルを選択を辞書に反映
            if self.level_dic[level] == False:
                self.level_dic[level] = True
            else:
                self.level_dic[level] = False

        #今選択されている難易度を取得
        msg = "選択されているレベル"
        for key, value in self.level_dic.items():
            if value:
                msg += f":{key}"

        #送信
        await interaction.response.send_message(msg)

    @ui.button(label="選択OK!!", style=discord.ButtonStyle.success)
    async def ok(self, button: discord.ui.Button, interaction: discord.Interaction):
        #対戦者かチェック
        if await self.check(button.user.id):
            #選択されたレベルをチェック
            ls = []
            for key, value in self.level_dic.items():
                if value:
                    ls.append(key)
            
            if len(ls) == 0:
                #レベルが選ばれてないとき
                await button.response.send_message("レベルが選択されてないよ！")
            else:
                #同じプレイヤーが再び押していないか
                if button.user.id in self.click:
                    await button.response.send_message("もう押してるよ！", ephemeral=True)
                else:
                    #ボタンをクリックした人を追加
                    self.click.append(button.user.id)
                    #二人ともがボタンを押したら処理を行う
                    if len(self.click) == 2:
                        #ボタンを無効化
                        self.children[0].disabled, self.children[1].disabled = True, True
                        await button.response.edit_message(view=self)
                        await button.followup.send(f"{button.user.display_name}がOKを選択したよ！ 課題曲を発表します！！")
                        #+を.7形式に変換
                        temp_ls = []
                        for lv in ls:
                            if lv[-1] == "+":
                                lv_f = float(lv[:-1]) + 0.7
                                temp_ls.append(lv_f)
                            else:
                                lv_f = float(lv)
                                temp_ls.append(lv_f)

                        #終了フラグを消す
                        self.stop_flg = False
                        #曲選択へ
                        await Arcaea_command.s_sb_musicselect(button, self.player[0], self.player[1], self.dif, temp_ls, self.EX_flg)
                    else:
                        await button.response.send_message(f"{button.user.display_name}がOKを選択したよ！")
        else:
            await button.response.send_message("きみは対戦者じゃないよ", ephemeral=True)


    async def check(self, user):
        """対戦者以外ではないか確認"""
        if user in self.player:
            return True #対戦者
        else:
            return False #それ以外


class VSMusicButton(ui.View):
    """課題曲選択ボタン"""
    def __init__(self, user1, user2, dif_ls, level_ls, music, EX_flg, Score_Count=None, timeout=180):
        self.player = [user1, user2]
        self.ok_click = []
        self.reroll_click = []
        self.dif_ls = dif_ls
        self.level_ls = level_ls
        self.music = music
        self.EX_flg = EX_flg
        self.Score_Count = Score_Count
        self.stop_flg = True
        super().__init__(timeout=timeout)

    @ui.button(label="OK!!", style=discord.ButtonStyle.success)
    async def ok(self, button: discord.ui.Button, interaction: discord.Interaction):
        """決定"""
        #対戦者かチェック
        flg = await self.check(button.user.id)
        if flg:
            #同じプレイヤーが再び押していないか
            if button.user.id in self.ok_click:
                await button.response.send_message("もう押してるよ！", ephemeral=True)
            else:
                #ボタンをクリックした人を追加
                self.ok_click.append(button.user.id)
                #二人ともがボタンを押したら対戦を行う
                if len(self.ok_click) == 2:
                    #ボタンを無効化
                    self.children[0].disabled, self.children[1].disabled = True, True
                    await button.response.edit_message(view=self)
                    #対戦開始をアナウンス
                    await button.followup.send(f"{button.user.display_name}さんがOKを押したよ！\n対戦スタート！！")
                    #終了フラグを消す
                    self.stop_flg = False
                    #対戦へ
                    await Arcaea_command.s_sb_battle(button, self.player[0], self.player[1], self.dif_ls, self.level_ls, self.music, self.EX_flg, self.Score_Count)
                else:
                    await button.response.send_message(f"{button.user.display_name}さんがOKを押したよ！")
        else:
            await button.response.send_message("きみは対戦者じゃないよ", ephemeral=True)

    @ui.button(label="引き直し", style=discord.ButtonStyle.blurple)
    async def exscore(self, button: discord.ui.Button, interaction: discord.Interaction):
        """引き直し"""
        #対戦者かチェック
        flg = await self.check(button.user.id)
        if flg:
            #同じプレイヤーが再び押していないか
            if button.user.id in self.reroll_click:
                await button.response.send_message("もう押してるよ！", ephemeral=True)
            else:
                #ボタンをクリックした人を追加
                self.reroll_click.append(button.user.id)
                #二人ともがボタンを押したら引き直しを行う
                if len(self.reroll_click) == 2:
                    #ボタンを無効化
                    self.children[0].disabled, self.children[1].disabled = True, True
                    await button.response.edit_message(view=self)
                    await button.followup.send(f"{button.user.display_name}さんが引き直しを押したよ\nなにがでるかな～～")
                    #終了フラグを消す
                    self.stop_flg = False
                    #抽選を行う
                    await Arcaea_command.s_sb_musicselect(button, self.player[0], self.player[1], self.dif_ls, self.level_ls, self.EX_flg, self.Score_Count)
                else:
                    await button.response.send_message(f"{button.user.display_name}さんが引き直しを押したよ")
        else:
            await button.response.send_message("きみは対戦者じゃないよ", ephemeral=True)


    async def check(self, user):
        """対戦者以外ではないか確認"""
        if user in self.player:
            return True #対戦者
        else:
            return False #それ以外


class VSScoreCheck(ui.View):
    """スコア確認ボタン"""
    def __init__(self, user, timeout=600):
        self.user_id = user
        self.start_flg = False
        self.reinput_flg = False
        super().__init__(timeout=timeout)

    @ui.button(label="OK!", style=discord.ButtonStyle.success)
    async def scoreok(self, button: discord.ui.Button, interaction: discord.Interaction):
        if button.user.id == self.user_id:
            self.start_flg = True
            await button.response.send_message("入力を確定したよ!!")
        else:
            await button.response.send_message("スコア入力者じゃないよ", ephemeral=True)

    @ui.button(label="入力しなおす", style=discord.ButtonStyle.gray)
    async def reinput(self, button: discord.ui.Button, interaction: discord.Interaction):
        if button.user.id == self.user_id:
            self.reinput_flg = True
            await button.response.send_message("スコアを入力し直してね")
        else:
            await button.response.send_message("スコア入力者じゃないよ", ephemeral=True)
