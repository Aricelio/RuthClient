using System.Windows.Forms;

namespace RuthClient.Presentation.Forms.PanelForm
{
    partial class PanelForm
    {
        /// <summary>Required designer variable.</summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>Clean up any resources being used.</summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>Required method for Designer support - do not modify the contents of this method with the code editor.</summary>
        private void InitializeComponent()
        {
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(PanelForm));
            mainMenu = new MenuStrip();
            fileToolStripMenuItem = new ToolStripMenuItem();
            collectionsToolStripMenuItem = new ToolStripMenuItem();
            environmentsToolStripMenuItem = new ToolStripMenuItem();
            settingsToolStripMenuItem = new ToolStripMenuItem();
            tabControl = new TabControl();
            tabPageDefault = new TabPage();
            textBoxUrl = new TextBox();
            comboBoxHttpMethods = new ComboBox();
            textAreaRequest = new TextBox();
            textAreaResponse = new TextBox();
            buttonSend = new Button();
            mainMenu.SuspendLayout();
            tabControl.SuspendLayout();
            tabPageDefault.SuspendLayout();
            SuspendLayout();
            // 
            // mainMenu
            // 
            mainMenu.ImageScalingSize = new Size(20, 20);
            mainMenu.Items.AddRange(new ToolStripItem[] { fileToolStripMenuItem, collectionsToolStripMenuItem, environmentsToolStripMenuItem, settingsToolStripMenuItem });
            mainMenu.Location = new Point(0, 0);
            mainMenu.Name = "mainMenu";
            mainMenu.Size = new Size(1395, 28);
            mainMenu.TabIndex = 0;
            mainMenu.Text = "mainMenu";
            // 
            // fileToolStripMenuItem
            // 
            fileToolStripMenuItem.AccessibleName = "File";
            fileToolStripMenuItem.Name = "fileToolStripMenuItem";
            fileToolStripMenuItem.Size = new Size(46, 24);
            fileToolStripMenuItem.Text = "&File";
            // 
            // collectionsToolStripMenuItem
            // 
            collectionsToolStripMenuItem.AccessibleName = "Collections";
            collectionsToolStripMenuItem.Name = "collectionsToolStripMenuItem";
            collectionsToolStripMenuItem.Size = new Size(96, 24);
            collectionsToolStripMenuItem.Text = "&Collections";
            // 
            // environmentsToolStripMenuItem
            // 
            environmentsToolStripMenuItem.AccessibleName = "Environments";
            environmentsToolStripMenuItem.Name = "environmentsToolStripMenuItem";
            environmentsToolStripMenuItem.Size = new Size(112, 24);
            environmentsToolStripMenuItem.Text = "&Environments";
            // 
            // settingsToolStripMenuItem
            // 
            settingsToolStripMenuItem.AccessibleName = "Settings";
            settingsToolStripMenuItem.Name = "settingsToolStripMenuItem";
            settingsToolStripMenuItem.Size = new Size(76, 24);
            settingsToolStripMenuItem.Text = "&Settings";
            // 
            // tabControl
            // 
            tabControl.Controls.Add(tabPageDefault);
            tabControl.Dock = DockStyle.Fill;
            tabControl.Location = new Point(0, 28);
            tabControl.Name = "tabControl";
            tabControl.SelectedIndex = 0;
            tabControl.Size = new Size(1395, 633);
            tabControl.TabIndex = 1;
            // 
            // tabPageDefault
            // 
            tabPageDefault.AccessibleName = "Default";
            tabPageDefault.Controls.Add(textBoxUrl);
            tabPageDefault.Controls.Add(comboBoxHttpMethods);
            tabPageDefault.Controls.Add(textAreaRequest);
            tabPageDefault.Controls.Add(textAreaResponse);
            tabPageDefault.Controls.Add(buttonSend);
            tabPageDefault.Location = new Point(4, 29);
            tabPageDefault.Name = "tabPageDefault";
            tabPageDefault.Padding = new Padding(3);
            tabPageDefault.Size = new Size(1387, 600);
            tabPageDefault.TabIndex = 0;
            tabPageDefault.Text = "Default";
            tabPageDefault.UseVisualStyleBackColor = true;
            // 
            // textBoxUrl
            // 
            textBoxUrl.AccessibleName = "URL Input";
            textBoxUrl.Location = new Point(126, 40);
            textBoxUrl.Name = "textBoxUrl";
            textBoxUrl.Size = new Size(1177, 27);
            textBoxUrl.TabIndex = 0;
            // 
            // comboBoxHttpMethods
            // 
            comboBoxHttpMethods.AccessibleName = "HTTP Methods";
            comboBoxHttpMethods.DropDownStyle = ComboBoxStyle.DropDownList;
            comboBoxHttpMethods.FormattingEnabled = true;
            comboBoxHttpMethods.Items.AddRange(new object[] { "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS" });
            comboBoxHttpMethods.Location = new Point(0, 39);
            comboBoxHttpMethods.Name = "comboBoxHttpMethods";
            comboBoxHttpMethods.Size = new Size(120, 28);
            comboBoxHttpMethods.TabIndex = 1;
            // 
            // textAreaRequest
            // 
            textAreaRequest.AccessibleName = "Request Area";
            textAreaRequest.Location = new Point(0, 94);
            textAreaRequest.Multiline = true;
            textAreaRequest.Name = "textAreaRequest";
            textAreaRequest.ScrollBars = ScrollBars.Vertical;
            textAreaRequest.Size = new Size(1384, 220);
            textAreaRequest.TabIndex = 2;
            // 
            // textAreaResponse
            // 
            textAreaResponse.AccessibleName = "Response Area";
            textAreaResponse.Location = new Point(0, 320);
            textAreaResponse.Multiline = true;
            textAreaResponse.Name = "textAreaResponse";
            textAreaResponse.ReadOnly = true;
            textAreaResponse.ScrollBars = ScrollBars.Vertical;
            textAreaResponse.Size = new Size(1387, 280);
            textAreaResponse.TabIndex = 3;
            // 
            // buttonSend
            // 
            buttonSend.AccessibleName = "Send Request";
            buttonSend.Location = new Point(1309, 38);
            buttonSend.Name = "buttonSend";
            buttonSend.Size = new Size(75, 28);
            buttonSend.TabIndex = 4;
            buttonSend.Text = "Send";
            buttonSend.UseVisualStyleBackColor = true;
            // 
            // PanelForm
            // 
            AutoScaleDimensions = new SizeF(8F, 20F);
            AutoScaleMode = AutoScaleMode.Font;
            ClientSize = new Size(1395, 661);
            Controls.Add(tabControl);
            Controls.Add(mainMenu);
            Icon = (Icon)resources.GetObject("$this.Icon");
            MainMenuStrip = mainMenu;
            Name = "PanelForm";
            Text = "RuthClient";
            mainMenu.ResumeLayout(false);
            mainMenu.PerformLayout();
            tabControl.ResumeLayout(false);
            tabPageDefault.ResumeLayout(false);
            tabPageDefault.PerformLayout();
            ResumeLayout(false);
            PerformLayout();

        }

        #endregion

        private System.Windows.Forms.MenuStrip mainMenu;
        private System.Windows.Forms.ToolStripMenuItem fileToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem collectionsToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem environmentsToolStripMenuItem;
        private System.Windows.Forms.ToolStripMenuItem settingsToolStripMenuItem;
        private System.Windows.Forms.TabControl tabControl;
        private TabPage tabPageDefault;
        private System.Windows.Forms.TextBox textBoxUrl;
        private System.Windows.Forms.TextBox textAreaRequest;
        private System.Windows.Forms.TextBox textAreaResponse;
        private System.Windows.Forms.ComboBox comboBoxHttpMethods;
        private System.Windows.Forms.Button buttonSend;
    }
}