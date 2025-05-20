using System.Globalization;
using System.Resources;
using System.ComponentModel; // Add this using directive

namespace RuthClient
{
    public partial class Main : Form
    {
        private ComponentResourceManager resources;

        public Main()
        {
            InitializeComponent();
            resources = new ComponentResourceManager(typeof(Main));
            this.Icon = new Icon("images/icon.ico"); // Set the form icon
        }

        private void Form1_Load(object sender, EventArgs e)
        {
        }
    }
}