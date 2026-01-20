"""
Display module for PDF Search Tool using Rich library.

This module provides a modern terminal UI with progress bars and live-updating
status tables using the Rich library, creating a "dashboard" feel.
"""

from typing import Optional
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TimeElapsedColumn
)
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich import box

from ..config import APP_NAME, VERSION

console = Console()


class ProgressDisplay:
    """
    Rich-based UI display for PDF search progress.
    
    Provides a professional terminal interface with:
    - Progress bar showing overall completion
    - Live status table showing current keyword, location, and status
    - Clean, dashboard-like appearance
    """
    
    def __init__(self):
        """Initialize the progress display."""
        self.progress = None
        self.task_id = None
        self.live = None
        self.current_keyword = ""
        self.current_location = ""
        self.current_status = ""
        
    def _create_status_table(self) -> Table:
        """
        Create a live-updating status table showing current processing info.
        
        Returns:
            Rich Table object with current status information
        """
        table = Table(
            show_header=True,
            header_style="bold cyan",
            box=box.ROUNDED,
            padding=(0, 1),
            expand=True
        )
        
        table.add_column("Field", style="bold yellow", width=20)
        table.add_column("Value", style="green")
        
        # Truncate keyword if too long
        keyword_display = self.current_keyword
        if len(keyword_display) > 40:
            keyword_display = keyword_display[:37] + "..."
        
        table.add_row("Current Keyword", keyword_display)
        table.add_row("Current Location", self.current_location)
        table.add_row("Status", self.current_status)
        
        return table
    
    def _create_progress_panel(self) -> Progress:
        """
        Create the progress bar component.
        
        Returns:
            Rich Progress object configured for keyword processing
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}", justify="left"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=console,
            expand=False
        )
    
    def _generate_layout(self) -> Panel:
        """
        Generate the complete dashboard layout.
        
        Returns:
            Rich Panel containing progress bar and status table
        """
        # Create status table
        status_table = self._create_status_table()
        
        # Create panel with both progress and status
        return Panel(
            status_table,
            title=f"[bold magenta]{APP_NAME} v{VERSION}[/bold magenta]",
            subtitle="[italic]Processing Keywords...[/italic]",
            border_style="cyan",
            box=box.DOUBLE
        )
    
    def start(self, total_keywords: int):
        """
        Start the progress display.
        
        Args:
            total_keywords: Total number of keywords to process
        """
        # Create progress bar
        self.progress = self._create_progress_panel()
        self.task_id = self.progress.add_task(
            "[cyan]Processing Keywords",
            total=total_keywords
        )
        
        # Initial status
        self.current_keyword = "Initializing..."
        self.current_location = ""
        self.current_status = "Starting..."
        
        # Start the progress bar
        self.progress.start()
        console.print()
    
    def update_progress(self, completed: int, total: int):
        """
        Update the progress bar.
        
        Args:
            completed: Number of keywords completed
            total: Total number of keywords
        """
        if self.progress and self.task_id is not None:
            self.progress.update(
                self.task_id,
                completed=completed,
                total=total,
                description=f"[cyan]Processing Keywords [{completed}/{total}]"
            )
    
    def update_status(self, keyword: str, location: str, status: str):
        """
        Update the status table with current processing information.
        
        Args:
            keyword: Current keyword being searched
            location: Current folder/location being scanned
            status: Current status message
        """
        self.current_keyword = keyword
        self.current_location = location
        self.current_status = status
    
    def display_status_table(self):
        """Display the current status table below the progress bar."""
        if self.progress:
            console.print()
            status_panel = self._generate_layout()
            console.print(status_panel)
    
    def stop(self):
        """Stop and cleanup the progress display."""
        if self.progress:
            self.progress.stop()
        console.print()


class SimpleProgressDisplay:
    """
    Simplified progress display that shows progress bar with periodic status updates.
    
    This is a simpler alternative to the full dashboard, showing just the progress
    bar with status information printed periodically.
    """
    
    def __init__(self):
        """Initialize the simple progress display."""
        self.progress = None
        self.task_id = None
        self.last_keyword = ""
        
    def start(self, total_keywords: int):
        """
        Start the progress display.
        
        Args:
            total_keywords: Total number of keywords to process
        """
        console.print()
        console.print(f"[bold magenta]{APP_NAME} v{VERSION}[/bold magenta]")
        console.print()
        
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}", justify="left"),
            BarColumn(bar_width=50),
            TaskProgressColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=console
        )
        
        self.task_id = self.progress.add_task(
            "[cyan]Processing Keywords",
            total=total_keywords
        )
        
        self.progress.start()
    
    def update_progress(self, completed: int, total: int):
        """
        Update the progress bar.
        
        Args:
            completed: Number of keywords completed
            total: Total number of keywords
        """
        if self.progress and self.task_id is not None:
            self.progress.update(
                self.task_id,
                completed=completed,
                total=total,
                description=f"[cyan]Processing Keywords [{completed}/{total}]"
            )
    
    def update_status(self, keyword: str, location: str, status: str):
        """
        Update status (just track the keyword for display).
        
        Args:
            keyword: Current keyword being searched
            location: Current folder/location being scanned
            status: Current status message
        """
        self.last_keyword = keyword
    
    def display_status_table(self):
        """
        Display status information.
        
        For simple display, we show a status table after each keyword is complete.
        """
        pass  # Status updates handled in progress bar description
    
    def stop(self):
        """Stop and cleanup the progress display."""
        if self.progress:
            self.progress.stop()
        console.print()


def print_header():
    """Print application header."""
    console.print()
    console.print(Panel.fit(
        f"[bold magenta]{APP_NAME}[/bold magenta]\n"
        f"[cyan]Version {VERSION}[/cyan]",
        border_style="magenta",
        box=box.DOUBLE
    ))
    console.print()


def print_summary(total: int, found: int, not_found: int, output_path: str):
    """
    Print a summary table of results.
    
    Args:
        total: Total number of keywords processed
        found: Number of keywords found
        not_found: Number of keywords not found
        output_path: Path to the output file
    """
    console.print()
    
    # Create summary table
    table = Table(
        title="[bold green]✓ Processing Complete[/bold green]",
        show_header=True,
        header_style="bold cyan",
        box=box.DOUBLE,
        border_style="green"
    )
    
    table.add_column("Metric", style="bold yellow", width=30)
    table.add_column("Value", style="green", justify="right")
    
    table.add_row("Total Keywords", str(total))
    table.add_row("Keywords Found", f"[bold green]{found}[/bold green]")
    table.add_row("Keywords Not Found", f"[bold red]{not_found}[/bold red]")
    table.add_row("Success Rate", f"{(found/total*100):.1f}%" if total > 0 else "0%")
    
    console.print(table)
    console.print()
    console.print(f"[bold cyan]Results saved to:[/bold cyan] [green]{output_path}[/green]")
    console.print()


def print_error(error_message: str):
    """
    Print an error message in a styled panel.
    
    Args:
        error_message: Error message to display
    """
    console.print()
    console.print(Panel(
        f"[bold red]✗ ERROR[/bold red]\n\n{error_message}",
        border_style="red",
        box=box.DOUBLE
    ))
    console.print()
