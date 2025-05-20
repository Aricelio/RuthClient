using RuthClient.Presentation.Forms.PanelForm;

namespace RuthClient
{
    internal static class Program
    {
        [STAThread]
        private static void Main()
        {
            ApplicationConfiguration.Initialize();
            Application.Run(new PanelForm());
        }
    }
}